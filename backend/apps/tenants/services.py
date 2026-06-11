"""
Service layer — app tenants.

Lógica de negocio para la configuración del complejo (ComplexSettings).
La creación de tenants vive en el management command create_tenant (ADR-009).

Regla: toda lógica de negocio vive en services.py, nunca en views ni serializers.
"""

from apps.tenants.models import ComplexSettings


def get_complex_settings() -> ComplexSettings:
    """
    Retorna la configuración del complejo activo (tenant actual).

    Usa get_or_create con complex_name vacío como default: siempre retorna
    una instancia válida, nunca lanza 404. El tenant activo lo determina
    el esquema de la conexión activa (middleware de django-tenants).

    Returns:
        ComplexSettings: instancia de configuración del complejo.
    """
    settings_obj, _ = ComplexSettings.objects.get_or_create(
        defaults={"complex_name": ""}
    )
    return settings_obj


def update_complex_settings(*, data: dict) -> ComplexSettings:
    """
    Actualiza los campos de la configuración del complejo activo.

    Semántica PATCH: solo actualiza los campos presentes en `data`.
    Los campos ausentes no se modifican. Si la configuración no existe
    la crea antes de actualizar.

    Args:
        data: dict con los campos a actualizar (subset de ComplexSettings).

    Returns:
        ComplexSettings: instancia actualizada.
    """
    settings_obj = get_complex_settings()

    for field, value in data.items():
        setattr(settings_obj, field, value)

    settings_obj.save()
    return settings_obj
