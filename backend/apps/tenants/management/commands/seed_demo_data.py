"""
Management command: seed_demo_data

Puebla un esquema de tenant con datos realistas para presentaciones.
Crea canchas, horarios, un operador y reservas en distintos estados.
Es idempotente: si los datos ya existen, no los duplica.

Uso:
    python manage.py seed_demo_data --schema demo
"""

import logging
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)

COURTS_DATA = [
    {
        "name": "Cancha 1 - Fútbol 5",
        "court_type": "futbol_5",
        "surface": "Césped sintético",
        "base_price": Decimal("18000"),
        "slot_duration_minutes": 60,
    },
    {
        "name": "Cancha 2 - Fútbol 5",
        "court_type": "futbol_5",
        "surface": "Césped sintético",
        "base_price": Decimal("18000"),
        "slot_duration_minutes": 60,
    },
    {
        "name": "Cancha 3 - Fútbol 7",
        "court_type": "futbol_7",
        "surface": "Césped sintético",
        "base_price": Decimal("25000"),
        "slot_duration_minutes": 90,
    },
    {
        "name": "Cancha 4 - Pádel",
        "court_type": "padel",
        "surface": "Moqueta",
        "base_price": Decimal("14000"),
        "slot_duration_minutes": 60,
    },
]

GUEST_NAMES = [
    ("Lucas Fernández", "1140001111"),
    ("Martín García", "1150002222"),
    ("Pablo Rodríguez", "1160003333"),
    ("Diego Martínez", "1170004444"),
    ("Sebastián López", "1140005555"),
    ("Nicolás Pérez", "1150006666"),
    ("Gonzalo Sánchez", "1160007777"),
    ("Andrés Torres", "1170008888"),
    ("Javier Moreno", "1140009999"),
    ("Ricardo Álvarez", "1150000001"),
    ("Facundo Castro", "1160000002"),
    ("Esteban Ortiz", "1170000003"),
    ("Matías Herrera", "1140000004"),
    ("Tomás Ramírez", "1140000101"),
    ("Ignacio Flores", "1150000102"),
    ("Agustín Reyes", "1160000103"),
    ("Bruno Vargas", "1170000104"),
]


class Command(BaseCommand):
    help = "Puebla un tenant con datos de demo para presentaciones (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            default="demo",
            help="Nombre del esquema del tenant (default: demo).",
        )

    def handle(self, *args, **options):
        schema_name = options["schema"]
        self.stdout.write(f"Sembrando datos de demo en schema '{schema_name}'...")

        with schema_context(schema_name):
            courts = self._seed_courts()
            operator = self._seed_operator()
            self._seed_bookings(courts, operator)

        self.stdout.write(self.style.SUCCESS("✓ Datos de demo listos."))

    def _seed_courts(self):
        from apps.courts.models import Court, ScheduleBlock

        courts = []
        for data in COURTS_DATA:
            court, created = Court.objects.get_or_create(
                name=data["name"],
                defaults=data,
            )
            courts.append(court)
            if created:
                self.stdout.write(f"  + Cancha: {court.name}")
                # Disponibilidad lunes a domingo, 8:00 a 23:00
                for weekday in range(7):
                    ScheduleBlock.objects.create(
                        court=court,
                        weekday=weekday,
                        open_time=time(8, 0),
                        close_time=time(23, 0),
                    )
            else:
                self.stdout.write(f"  · Cancha ya existe: {court.name}")
        return courts

    def _seed_operator(self):
        User = get_user_model()
        operator, created = User.objects.get_or_create(
            email="operador@demo.com",
            defaults={"role": "operator", "is_staff": True},
        )
        if created:
            operator.set_password("demo1234")
            operator.save()
            self.stdout.write("  + Operador: operador@demo.com / demo1234")
        else:
            self.stdout.write("  · Operador ya existe: operador@demo.com")
        return operator

    def _seed_bookings(self, courts, operator):
        from apps.bookings.models import Booking, CashMovement

        now = timezone.now()
        # Argentina = UTC-3; 9:00 AR = 12:00 UTC
        base_today = now.replace(hour=12, minute=0, second=0, microsecond=0)

        guest_idx = 0

        def next_guest():
            nonlocal guest_idx
            g = GUEST_NAMES[guest_idx % len(GUEST_NAMES)]
            guest_idx += 1
            return g

        def make_booking(court, start, status, notes=""):
            name, phone = next_guest()
            end = start + timedelta(minutes=court.slot_duration_minutes)
            booking, created = Booking.objects.get_or_create(
                court=court,
                start_dt=start,
                defaults={
                    "guest_name": name,
                    "guest_phone": phone,
                    "end_dt": end,
                    "status": status,
                    "price": court.base_price,
                },
            )
            if created:
                self.stdout.write(f"  + Reserva {status}: {name} — {court.name}")
                if status == Booking.Status.CONFIRMED:
                    CashMovement.objects.create(
                        booking=booking,
                        operator=operator,
                        amount=court.base_price,
                        notes=notes or "Seña confirmada por transferencia",
                    )
            return booking

        # ── Reservas pasadas (últimos 7 días) ── COMPLETED
        for days_ago in range(1, 8):
            for court in courts:
                hour_utc = 12 + (days_ago % 3) * 2  # varía entre 12, 14, 16 UTC
                start = base_today - timedelta(days=days_ago) + timedelta(hours=hour_utc - 12)
                make_booking(court, start, Booking.Status.COMPLETED, "Seña cobrada en efectivo")

        # ── Una reserva cancelada ──
        court = courts[0]
        start = base_today - timedelta(days=3) + timedelta(hours=2)
        name, phone = next_guest()
        end = start + timedelta(minutes=court.slot_duration_minutes)
        Booking.objects.get_or_create(
            court=court,
            start_dt=start,
            defaults={
                "guest_name": name,
                "guest_phone": phone,
                "end_dt": end,
                "status": Booking.Status.CANCELLED,
                "price": court.base_price,
                "cancellation_reason": "El jugador canceló por motivos personales",
            },
        )
        self.stdout.write(f"  + Reserva CANCELLED: {name}")

        # ── Reservas de hoy ── CONFIRMED y PENDING_PAYMENT
        today_slots = [
            (courts[0], 1, Booking.Status.CONFIRMED),
            (courts[1], 2, Booking.Status.CONFIRMED),
            (courts[2], 3, Booking.Status.PENDING_PAYMENT),
            (courts[3], 4, Booking.Status.PENDING_PAYMENT),
            (courts[0], 5, Booking.Status.PENDING_PAYMENT),
            (courts[1], 6, Booking.Status.PENDING_PAYMENT),
        ]
        for court, hour_offset, status in today_slots:
            start = base_today + timedelta(hours=hour_offset)
            if start < now:
                start = now + timedelta(hours=hour_offset)
            make_booking(court, start, status)

        # ── Reservas futuras (próximos 4 días) ── PENDING_PAYMENT
        for days_ahead in range(1, 5):
            for i, court in enumerate(courts):
                start = base_today + timedelta(days=days_ahead) + timedelta(hours=i * 2)
                make_booking(court, start, Booking.Status.PENDING_PAYMENT)
