"""
Custom User model — SaaS Gestión de Canchas

ADR-007: User en TENANT_APPS (por tenant, no compartido en public).
  Cada complejo tiene su propia tabla de usuarios en su esquema PostgreSQL.
  Un usuario no existe ni es visible en otro complejo.

FIX R-08: Identificador de login unificado en `email`.
  USERNAME_FIELD = "email" hace que Django Auth, SimpleJWT y los management
  commands de Django usen email como identificador principal. El campo
  `username` se elimina (no era un requisito de negocio; la marca blanca
  solo necesita email + password). Se provee un manager custom (UserManager)
  que implementa create_user y create_superuser sin username.

Roles (RBAC.md):
  tenant_admin — dueño/admin del complejo (configura canchas, ve caja, gestiona usuarios)
  operator     — cajero/recepcionista (confirma reservas, registra señas)
  player       — jugador/cliente final (ve grilla, crea reservas)

El system_admin es el superuser del esquema public (gestiona tenants, no es un rol aquí).

Reglas:
  - Soft-delete: is_active (heredado de AbstractBaseUser).
  - Timestamps: created_at, updated_at.
  - Fechas en UTC (USE_TZ=True en settings).
  - Prohibido DELETE físico.

Nota de migración:
  No existe 0001_initial para esta app todavía. La primera migración se genera
  con `python manage.py makemigrations users` dentro del contenedor Docker y
  capturará este modelo como estado inicial limpio.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Manager custom que usa `email` como identificador único en lugar de `username`.

    Implementa los dos métodos requeridos por Django:
      create_user        — usuario normal (is_staff=False, is_superuser=False)
      create_superuser   — superusuario (is_staff=True, is_superuser=True)

    Ambos métodos normalizan el email y requieren password explícito.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Crea y persiste un usuario normal con email y password.

        El campo `role` acepta los valores de User.Role; el default (PLAYER)
        proviene de la definición del campo en el modelo.
        """
        if not email:
            raise ValueError("El email es obligatorio.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Crea un superusuario. Usado por `manage.py createsuperuser`.
        Los superusuarios del esquema `public` son el system_admin de la plataforma.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Usuario custom del sistema.

    Hereda de AbstractBaseUser (en lugar de AbstractUser) para tener control
    total sobre el identificador de login. El email es el único identificador;
    no existe campo `username` (no es un requisito de negocio en una app
    marca blanca donde el jugador se identifica por email).

    Campos heredados de AbstractBaseUser:
      password, last_login, is_active

    Campos heredados de PermissionsMixin:
      is_superuser, groups, user_permissions

    Campo `is_active`: soft-delete (True = activo). Prohibido DELETE físico.
    """

    class Role(models.TextChoices):
        TENANT_ADMIN = "tenant_admin", "Admin del complejo"
        OPERATOR = "operator", "Cajero / Recepcionista"
        PLAYER = "player", "Jugador"

    # Identificador de login (FIX R-08)
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Dirección de correo electrónico. Es el identificador de login.",
    )

    # Datos personales opcionales
    first_name = models.CharField(max_length=150, blank=True, verbose_name="Nombre")
    last_name = models.CharField(max_length=150, blank=True, verbose_name="Apellido")

    # RBAC
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PLAYER,
        verbose_name="Rol",
        help_text=(
            "Rol del usuario en el complejo. "
            "tenant_admin: dueño/admin. "
            "operator: cajero/recepcionista. "
            "player: jugador/cliente."
        ),
    )

    # Permisos de staff para el admin de Django
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Es staff",
        help_text="Permite acceso al admin de Django.",
    )

    # Soft-delete: is_active = False desactiva el usuario sin borrarlo físicamente
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Desmarcar en lugar de borrar (soft-delete).",
    )

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="Fecha de registro")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    # FIX R-08: email como identificador de login (en lugar del username por defecto)
    USERNAME_FIELD = "email"

    # Campos solicitados por `createsuperuser` además del USERNAME_FIELD.
    # No incluimos email (ya es USERNAME_FIELD) ni password (siempre se pide).
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        return self.first_name or self.email

    # ---------------------------------------------------------------------------
    # Propiedades de conveniencia para checks de permisos en views/permissions.py
    # ---------------------------------------------------------------------------

    @property
    def is_tenant_admin(self) -> bool:
        return self.role == self.Role.TENANT_ADMIN

    @property
    def is_operator(self) -> bool:
        return self.role == self.Role.OPERATOR

    @property
    def is_player(self) -> bool:
        return self.role == self.Role.PLAYER

    @property
    def is_staff_of_complex(self) -> bool:
        """True si el usuario es tenant_admin u operator (staff del complejo)."""
        return self.role in (self.Role.TENANT_ADMIN, self.Role.OPERATOR)
