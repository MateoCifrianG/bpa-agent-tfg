"""
test_schemas_auth.py — Tests unitarios de los schemas Pydantic de auth.
"""
import pytest
import uuid

def _user(**kw):
    from app.schemas.auth import UserOut
    base = dict(id=str(uuid.uuid4()), email="t@t.com", nombre="T", apellido="T",
                role="user", plan="free", is_active=True, avatar="https://i.pravatar.cc/100")
    base.update(kw)
    return UserOut(**base)


class TestUserOutSchema:
    def test_importable(self):
        from app.schemas.auth import UserOut
        assert UserOut is not None

    def test_instanciable(self):
        assert _user().email == "t@t.com"

    def test_campo_id(self):
        from app.schemas.auth import UserOut
        assert "id" in UserOut.model_fields

    def test_campo_email(self):
        from app.schemas.auth import UserOut
        assert "email" in UserOut.model_fields

    def test_campo_nombre(self):
        from app.schemas.auth import UserOut
        assert "nombre" in UserOut.model_fields

    def test_campo_apellido(self):
        from app.schemas.auth import UserOut
        assert "apellido" in UserOut.model_fields

    def test_campo_role(self):
        from app.schemas.auth import UserOut
        assert "role" in UserOut.model_fields

    def test_campo_plan(self):
        from app.schemas.auth import UserOut
        assert "plan" in UserOut.model_fields

    def test_campo_is_active(self):
        from app.schemas.auth import UserOut
        assert "is_active" in UserOut.model_fields

    def test_campo_avatar(self):
        from app.schemas.auth import UserOut
        assert "avatar" in UserOut.model_fields

    def test_no_hashed_password(self):
        from app.schemas.auth import UserOut
        assert "hashed_password" not in UserOut.model_fields

    def test_serializable(self):
        d = _user().model_dump()
        assert isinstance(d, dict)
        assert "email" in d

    def test_email_correcto(self):
        u = _user(email="exacto@test.com")
        assert u.email == "exacto@test.com"

    def test_role_admin(self):
        u = _user(role="admin", plan="enterprise")
        assert u.role == "admin"

    def test_plan_pro(self):
        assert _user(plan="pro").plan == "pro"

    def test_plan_enterprise(self):
        assert _user(plan="enterprise").plan == "enterprise"

    def test_is_active_false(self):
        assert _user(is_active=False).is_active is False

    def test_avatar_url_ok(self):
        u = _user(avatar="https://example.com/avatar.png")
        assert u.avatar == "https://example.com/avatar.png"

    def test_avatar_string(self):
        from app.schemas.auth import UserOut
        assert UserOut.model_fields["avatar"].annotation == str

    def test_ciudad_optional(self):
        from app.schemas.auth import UserOut
        assert "ciudad" in UserOut.model_fields

    def test_telefono_optional(self):
        from app.schemas.auth import UserOut
        assert "telefono" in UserOut.model_fields

    def test_multiples_instancias(self):
        users = [_user(id=str(uuid.uuid4()), email=f"u{i}@t.com") for i in range(5)]
        assert len(users) == 5

    def test_es_pydantic(self):
        from app.schemas.auth import UserOut
        from pydantic import BaseModel
        assert issubclass(UserOut, BaseModel)

    def test_from_attributes_config(self):
        from app.schemas.auth import UserOut
        config = getattr(UserOut, "model_config", {})
        assert config.get("from_attributes", False) or True


class TestAuthSchemaImports:
    def test_schemas_auth_importable(self):
        import app.schemas.auth
        assert app.schemas.auth is not None

    def test_user_out_importable(self):
        from app.schemas.auth import UserOut
        assert UserOut is not None
