"""
test_empresas_avanzado.py — Tests avanzados de empresa: actualización sectorial,
límites de campos, validaciones, aislamiento, edge cases.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestEmpresaGet:
    async def test_get_empresa_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia")
        assert r.status_code == 401

    async def test_get_empresa_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert r.status_code == 200

    async def test_get_empresa_devuelve_dict(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert isinstance(r.json(), dict)

    async def test_empresa_tiene_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "id" in data

    async def test_empresa_tiene_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "nombre" in data

    async def test_empresa_tiene_sector(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "sector" in data

    async def test_empresa_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")

    async def test_empresa_no_expone_datos_sensibles(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert "$2b$" not in r.text
        assert "hashed_password" not in r.text.lower()

    async def test_admin_tiene_empresa(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/empresa/mia", headers=admin_headers)
        assert r.status_code == 200

    async def test_empresa_aislada_por_usuario(self, client: AsyncClient, test_user, auth_headers,
                                                admin_user, admin_headers):
        r_user = await client.get("/api/empresa/mia", headers=auth_headers)
        r_admin = await client.get("/api/empresa/mia", headers=admin_headers)
        assert r_user.json()["id"] != r_admin.json()["id"]


class TestEmpresaUpdate:
    async def test_update_empresa_requiere_auth(self, client: AsyncClient):
        r = await client.put("/api/empresa/mia", json={"nombre": "Nueva Empresa"})
        assert r.status_code in (401, 403)

    async def test_update_empresa_nombre_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "Empresa Actualizada Test"
        })
        assert r.status_code == 200

    async def test_update_empresa_nombre_se_guarda(self, client: AsyncClient, test_user, auth_headers):
        uid = uuid.uuid4().hex[:6]
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": f"Empresa {uid}"
        })
        assert r.status_code == 200
        if "nombre" in r.json():
            assert uid in r.json()["nombre"]

    async def test_update_empresa_sector_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "sector": "finanzas"
        })
        assert r.status_code == 200

    async def test_update_empresa_empleados_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "empleados": 50
        })
        assert r.status_code == 200

    async def test_update_empresa_preserva_id(self, client: AsyncClient, test_user, auth_headers):
        r_get = await client.get("/api/empresa/mia", headers=auth_headers)
        original_id = r_get.json()["id"]
        r_put = await client.put("/api/empresa/mia", headers=auth_headers, json={"nombre": "New Name"})
        assert r_put.status_code == 200
        assert r_put.json().get("id") == original_id

    async def test_update_empresa_campos_extra_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "Empresa Test Extra",
            "campo_falso": "valor_falso",
        })
        assert r.status_code == 200
        assert "campo_falso" not in r.json()

    async def test_update_multiples_campos_empresa(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "Empresa Multi Update",
            "sector": "tecnología",
            "empleados": 100,
        })
        assert r.status_code == 200
        data = r.json()
        if "nombre" in data:
            assert data["nombre"] == "Empresa Multi Update"


class TestEmpresaValidaciones:
    async def test_nombre_empresa_muy_largo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "E" * 300
        })
        assert r.status_code in (200, 422)

    async def test_empleados_negativo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "empleados": -10
        })
        assert r.status_code in (200, 422)

    async def test_empleados_muy_grande(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "empleados": 999999
        })
        assert r.status_code in (200, 422)

    async def test_sector_con_acento(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "sector": "logística"
        })
        assert r.status_code == 200

    async def test_nombre_con_caracteres_especiales(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "Empresa & Socios S.L."
        })
        assert r.status_code == 200


class TestEmpresaSectores:
    async def test_sector_ventas(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "ventas"})
        assert r.status_code == 200

    async def test_sector_finanzas(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "finanzas"})
        assert r.status_code == 200

    async def test_sector_tecnologia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "tecnología"})
        assert r.status_code == 200

    async def test_sector_logistica(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "logística"})
        assert r.status_code == 200

    async def test_sector_rrhh(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "recursos humanos"})
        assert r.status_code == 200

    async def test_sector_marketing(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "marketing"})
        assert r.status_code == 200


class TestEmpresaEdgeCases:
    async def test_body_vacio_ok_o_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={})
        assert r.status_code in (200, 422)

    async def test_empresa_logo_campo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        if "logo" in data:
            assert data["logo"] is None or isinstance(data["logo"], str)

    async def test_update_empresa_token_invalido_401(self, client: AsyncClient):
        r = await client.put("/api/empresa/mia",
                             headers={"Authorization": "Bearer invalidtoken"},
                             json={"nombre": "X"})
        assert r.status_code == 401

    async def test_get_empresa_token_invalido_401(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia",
                             headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code == 401
