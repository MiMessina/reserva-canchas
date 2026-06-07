"""
Tests de concurrencia — motor de reservas — Sprint 2

Cobertura:
  1. Dos hilos intentan crear la misma reserva simultáneamente:
     solo UNA debe tener éxito y la otra debe fallar con SLOT_ALREADY_BOOKED.
  2. Dos hilos reservan slots distintos en la misma cancha: ambos ganan.

Patrón:
  django_tenants no provee TenantTransactionTestCase en esta versión.
  Se usa django.test.TransactionTestCase + manejo manual del schema
  con schema_context() en cada hilo para que select_for_update() opere
  en transacciones reales (sin el rollback automático de TestCase).

  El tenant de prueba se crea en setUpClass() y se migra manualmente.
  Cada hilo activa el schema_context antes de llamar al service.

NOTA: se usa django.test.TransactionTestCase (no pytest-django db fixture)
porque necesitamos control total del ciclo de vida de la transacción.
La anotación @pytest.mark.django_db(transaction=True) no es suficiente
en el contexto multi-tenant porque no configura el search_path.
"""

import threading
from datetime import datetime, timezone as tz

from django.db import connection
from django.test import TransactionTestCase
from django_tenants.utils import schema_context

from apps.tenants.models import Domain, Tenant


class TestBookingConcurrency(TransactionTestCase):
    """
    Test de concurrencia del motor de reservas.

    Usa TransactionTestCase para que cada hilo pueda tener su propia
    transacción de base de datos real (el select_for_update() requiere esto).
    """

    # Nombre único de schema para no colisionar con otros tests
    SCHEMA_NAME = "test_concurrency_bookings"
    DOMAIN_NAME = "concurrency.test.localhost"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.conf import settings
        if cls.DOMAIN_NAME not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS += [cls.DOMAIN_NAME]

    @classmethod
    def tearDownClass(cls):
        from django.conf import settings
        if cls.DOMAIN_NAME in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.remove(cls.DOMAIN_NAME)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # Crear el tenant de prueba para concurrencia en el schema public
        connection.set_schema_to_public()
        self.tenant = Tenant(schema_name=self.SCHEMA_NAME, name="Complejo Concurrencia Test")
        self.tenant.save()  # auto_create_schema=True: migra el esquema
        Domain.objects.create(
            domain=self.DOMAIN_NAME,
            tenant=self.tenant,
            is_primary=True,
        )

        # Crear cancha y bloque en el schema del tenant de prueba
        from apps.courts.models import Court, ScheduleBlock
        with schema_context(self.SCHEMA_NAME):
            self.court = Court.objects.create(
                name="Cancha Concurrencia",
                court_type="futbol_5",
                surface="",
                base_price="5000.00",
                slot_duration_minutes=60,
            )
            ScheduleBlock.objects.create(
                court=self.court,
                weekday=0,  # lunes
                open_time="08:00",
                close_time="22:00",
            )

    def tearDown(self):
        connection.set_schema_to_public()
        try:
            Domain.objects.filter(tenant=self.tenant).delete()
            self.tenant.delete(force_drop=True)
        except Exception:
            pass
        super().tearDown()

    def test_concurrent_booking_only_one_wins(self):
        """
        Dos hilos intentan reservar el mismo slot simultáneamente.
        Exactamente una reserva debe tener éxito; la otra debe fallar con SLOT_ALREADY_BOOKED.
        """
        from apps.bookings.services import create_booking

        # Lunes 2027-01-04 12:00 UTC = 09:00 Buenos Aires (dentro del bloque 08:00-22:00)
        start_dt = datetime(2027, 1, 4, 12, 0, tzinfo=tz.utc)
        court_id = self.court.pk
        schema_name = self.SCHEMA_NAME

        results = []
        errors = []
        lock = threading.Lock()

        def attempt_booking(guest_index: int):
            """Función ejecutada por cada hilo para intentar crear una reserva."""
            try:
                with schema_context(schema_name):
                    booking = create_booking(
                        court_id=court_id,
                        start_dt=start_dt,
                        guest_name=f"Jugador Concurrente {guest_index}",
                        guest_phone=f"111111111{guest_index}",
                    )
                    with lock:
                        results.append(booking.pk)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        t1 = threading.Thread(target=attempt_booking, args=(1,))
        t2 = threading.Thread(target=attempt_booking, args=(2,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactamente una reserva debe haber tenido éxito
        self.assertEqual(
            len(results),
            1,
            f"Se esperaba exactamente 1 reserva exitosa, hubo {len(results)}. "
            f"Resultados: {results}. Errores: {errors}",
        )

        # Exactamente un error de overbooking
        self.assertEqual(
            len(errors),
            1,
            f"Se esperaba exactamente 1 error, hubo {len(errors)}. "
            f"Resultados: {results}. Errores: {errors}",
        )

        # El error debe contener SLOT_ALREADY_BOOKED
        self.assertIn(
            "SLOT_ALREADY_BOOKED",
            errors[0],
            f"Se esperaba SLOT_ALREADY_BOOKED en el error, se obtuvo: {errors[0]}",
        )

    def test_concurrent_booking_different_slots_both_win(self):
        """
        Dos hilos reservan slots DISTINTOS en la misma cancha.
        Ambos deben tener éxito (no hay solapamiento).
        """
        from apps.bookings.services import create_booking

        schema_name = self.SCHEMA_NAME
        court_id = self.court.pk

        # Slots distintos sin solapamiento: 13:00 y 14:00 UTC
        slot1 = datetime(2027, 1, 4, 13, 0, tzinfo=tz.utc)
        slot2 = datetime(2027, 1, 4, 14, 0, tzinfo=tz.utc)

        results = []
        errors = []
        lock = threading.Lock()

        def attempt_booking(slot, index):
            try:
                with schema_context(schema_name):
                    booking = create_booking(
                        court_id=court_id,
                        start_dt=slot,
                        guest_name=f"Jugador Distinto {index}",
                        guest_phone=f"222222222{index}",
                    )
                    with lock:
                        results.append(booking.pk)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        t1 = threading.Thread(target=attempt_booking, args=(slot1, 1))
        t2 = threading.Thread(target=attempt_booking, args=(slot2, 2))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(
            len(results),
            2,
            f"Ambos hilos debían tener éxito en slots distintos. "
            f"Resultados: {results}. Errores: {errors}",
        )
        self.assertEqual(
            len(errors),
            0,
            f"No debía haber errores para slots distintos. Errores: {errors}",
        )
