"""
Service layer — app users

Sprint 0: placeholder. La lógica de creación de usuarios vive aquí
cuando se implemente el registro de players o la gestión de staff.

Regla: toda lógica de negocio vive en services.py, nunca en views ni serializers.

Expansión Sprint 1+:
  - register_player(*, email, password, first_name, last_name) -> User
  - create_operator(*, email, password, created_by: User) -> User
    (solo tenant_admin puede crear operators)
"""
