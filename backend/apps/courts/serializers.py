"""
Serializers — app courts

Los serializers validan estructura y transforman datos; NO gobiernan negocio (RULES.md §1).
La lógica de negocio (validaciones de solapamiento, soft-delete) vive en services.py.

Serializers:
  CourtSerializer         — lectura (lista y detalle).
  CourtWriteSerializer    — escritura (crear / editar). Llama al service en la view.
  ScheduleBlockSerializer — lectura y escritura de bloques horarios.
                            El método create/update delega a services.py desde la view.
"""

from rest_framework import serializers

from apps.courts.models import Court, ScheduleBlock, SlotBlock


class CourtSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Court.

    Expone todos los campos públicos de una cancha.
    Usado en GET list y GET detail.
    """

    court_type_display = serializers.CharField(
        source="get_court_type_display",
        read_only=True,
        help_text="Etiqueta legible del tipo de cancha.",
    )

    class Meta:
        model = Court
        fields = [
            "id",
            "name",
            "court_type",
            "court_type_display",
            "surface",
            "base_price",
            "slot_duration_minutes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CourtWriteSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para Court.

    Usado en POST create y PATCH update. Solo valida estructura; la lógica
    de negocio se ejecuta en services.py desde la view.
    """

    class Meta:
        model = Court
        fields = [
            "name",
            "court_type",
            "surface",
            "base_price",
            "slot_duration_minutes",
            "is_active",
        ]


class ScheduleBlockSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura y escritura para ScheduleBlock.

    Para escritura el campo court acepta el PK de la cancha.
    La validación de negocio (open < close, solapamiento) se ejecuta
    en services.py, no aquí.

    weekday_display expone el nombre del día en español para el frontend.
    """

    weekday_display = serializers.CharField(
        source="get_weekday_display",
        read_only=True,
        help_text="Nombre del día de la semana en español.",
    )
    court_name = serializers.CharField(
        source="court.name",
        read_only=True,
        help_text="Nombre de la cancha asociada.",
    )

    class Meta:
        model = ScheduleBlock
        fields = [
            "id",
            "court",
            "court_name",
            "weekday",
            "weekday_display",
            "open_time",
            "close_time",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "court_name", "weekday_display", "is_active", "created_at", "updated_at"]


class SlotBlockSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura y escritura para SlotBlock.

    Expone los campos del bloqueo manual de slots.
    El campo created_by y is_active son de solo lectura (los asigna la view/service).
    start_dt y end_dt son datetime timezone-aware en UTC.

    Permisos de escritura: operator o tenant_admin (controlado en la view).
    """

    court_name = serializers.CharField(
        source="court.name",
        read_only=True,
        help_text="Nombre de la cancha bloqueada.",
    )

    class Meta:
        model = SlotBlock
        fields = [
            "id",
            "court",
            "court_name",
            "start_dt",
            "end_dt",
            "reason",
            "created_by",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "court_name", "created_by", "is_active", "created_at"]
