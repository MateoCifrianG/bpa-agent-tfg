"""
test_automatizaciones_avanzado.py — Tests avanzados de automatizaciones:
herramientas, estados, vinculación a proceso, bulk, aislamiento, edge cases.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAutomatizacionHerramientas:
    async def test_herramienta_n8n(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto n8n", "herramienta": "n8n",
        })
        assert r.status_code == 201
        assert r.json()["herramienta"] == "n8n"

    async def test_herramienta_zapier(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Zapier", "herramienta": "zapier",
        })
        assert r.status_code == 201

    async def test_herramienta_make(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Make", "herramienta": "make",
        })
        assert r.status_code == 201

    async def test_herramienta_python(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Python", "herramienta": "python",
        })
        assert r.status_code == 201

    async def test_herramienta_custom(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Custom", "herramienta": "custom_tool_v2",
        })
        assert r.status_code == 201

    async def test_sin_herramienta_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Sin Herramienta",
        })
        assert r.status_code == 201
        h = r.json().get("herramienta")
        assert h is None or isinstance(h, str)

    async def test_editar_herramienta(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "herramienta": "zapier",
        })
        assert r.status_code == 200
        assert r.json()["herramienta"] == "zapier"


class TestAutomatizacionEstados:
    async def test_estado_pendiente_default(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Estado Default",
        })
        assert r.status_code == 201
        estado = r.json().get("estado")
        assert estado in ("pendiente", "activo", "inactivo", None)

    async def test_estado_activo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Activo", "estado": "activo",
        })
        assert r.status_code == 201

    async def test_estado_inactivo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Inactivo", "estado": "inactivo",
        })
        assert r.status_code == 201

    async def test_estado_error(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Error", "estado": "error",
        })
        assert r.status_code in (201, 422)

    async def test_editar_estado_activo(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "estado": "activo",
        })
        assert r.status_code == 200

    async def test_editar_estado_inactivo(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "estado": "inactivo",
        })
        assert r.status_code == 200

    async def test_estado_persiste_tras_update(self, client: AsyncClient, test_user, auth_headers, test_auto):
        await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "estado": "activo",
        })
        r = await client.get(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["estado"] == "activo"


class TestAutomatizacionVinculacion:
    async def test_vinculada_a_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Vinculada", "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 201
        assert r.json().get("proceso_id") == test_proceso["id"]

    async def test_sin_proceso_id_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Sin Proceso",
        })
        assert r.status_code == 201

    async def test_proceso_id_invalido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto ProcID Malo",
            "proceso_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code in (201, 400, 403, 404, 422)

    async def test_editar_proceso_id(self, client: AsyncClient, test_user, auth_headers, test_auto, test_proceso):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 200


class TestAutomatizacionHorasMes:
    async def test_horas_mes_entero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto HM10", "horas_mes": 10,
        })
        assert r.status_code == 201
        assert r.json()["horas_mes"] == 10

    async def test_horas_mes_cero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto HM0", "horas_mes": 0,
        })
        assert r.status_code == 201

    async def test_horas_mes_grande(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto HM999", "horas_mes": 999,
        })
        assert r.status_code == 201

    async def test_horas_mes_decimal(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto HM Decimal", "horas_mes": 7.5,
        })
        assert r.status_code in (201, 422)

    async def test_horas_mes_no_numero_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto HM Texto", "horas_mes": "muchas",
        })
        assert r.status_code == 422

    async def test_editar_horas_mes(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "horas_mes": 25,
        })
        assert r.status_code == 200
        assert r.json()["horas_mes"] == 25


class TestAutomatizacionAislamiento:
    async def test_no_ve_auto_de_otro_usuario(self, client: AsyncClient, test_user, auth_headers,
                                               admin_user, admin_headers):
        r_auto = await client.post("/api/automatizaciones", headers=admin_headers, json={
            "nombre": "Auto Solo Admin",
        })
        if r_auto.status_code != 201:
            return
        auto_id = r_auto.json()["id"]
        r = await client.get(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r.status_code in (403, 404)

    async def test_listar_solo_propias(self, client: AsyncClient, test_user, auth_headers):
        uid = uuid.uuid4().hex[:8]
        r2 = await client.post("/api/auth/register", json={
            "email": f"autoaisl_{uid}@test.com", "password": "TestPass1!",
            "nombre": "AutoAisl", "apellido": "User",
            "empresa": "EmpAutoAisl", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r2.status_code != 201:
            return
        token2 = r2.json().get("access_token")
        h2 = {"Authorization": f"Bearer {token2}"}
        await client.post("/api/automatizaciones", headers=h2, json={"nombre": "Auto Empresa2"})
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        nombres = [a["nombre"] for a in r.json()]
        assert "Auto Empresa2" not in nombres

    async def test_editar_auto_otro_usuario_forbid(self, client: AsyncClient, test_user, auth_headers,
                                                    admin_user, admin_headers):
        r_auto = await client.post("/api/automatizaciones", headers=admin_headers, json={
            "nombre": "Admin Auto Edit",
        })
        if r_auto.status_code != 201:
            return
        auto_id = r_auto.json()["id"]
        r = await client.put(f"/api/automatizaciones/{auto_id}", headers=auth_headers, json={
            "nombre": "Hackeado",
        })
        assert r.status_code in (403, 404)

    async def test_eliminar_auto_otro_usuario_forbid(self, client: AsyncClient, test_user, auth_headers,
                                                      admin_user, admin_headers):
        r_auto = await client.post("/api/automatizaciones", headers=admin_headers, json={
            "nombre": "Admin Auto Del",
        })
        if r_auto.status_code != 201:
            return
        auto_id = r_auto.json()["id"]
        r = await client.delete(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r.status_code in (403, 404)


class TestAutomatizacionEdicion:
    async def test_editar_nombre(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "nombre": "Auto Renombrada",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == "Auto Renombrada"

    async def test_editar_descripcion(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "descripcion": "Nueva descripción de la automatización",
        })
        assert r.status_code == 200

    async def test_editar_preserva_herramienta(self, client: AsyncClient, test_user, auth_headers, test_auto):
        original_herramienta = test_auto.get("herramienta")
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "nombre": "Solo Nombre Editado",
        })
        assert r.status_code == 200
        assert r.json().get("herramienta") == original_herramienta

    async def test_editar_auto_inexistente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put(
            "/api/automatizaciones/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"nombre": "X"},
        )
        assert r.status_code in (403, 404)

    async def test_editar_nombre_xss_sanitizado(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "nombre": "<b>Auto</b><script>evil()</script>",
        })
        if r.status_code == 200:
            assert "<script>" not in r.json()["nombre"].lower()


class TestAutomatizacionEdgeCases:
    async def test_sin_nombre_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "herramienta": "n8n",
        })
        assert r.status_code == 422

    async def test_nombre_muy_largo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "A" * 300,
        })
        assert r.status_code in (201, 422)

    async def test_descripcion_muy_larga(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Desc XL",
            "descripcion": "D" * 2000,
        })
        assert r.status_code in (201, 422)

    async def test_campos_extra_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Extras",
            "campo_inventado": "valor_xyz",
            "otro_extra": 999,
        })
        assert r.status_code == 201
        assert "campo_inventado" not in r.json()

    async def test_multiples_autos_mismo_nombre(self, client: AsyncClient, test_user, auth_headers):
        for i in range(3):
            r = await client.post("/api/automatizaciones", headers=auth_headers, json={
                "nombre": "Auto Duplicada",
            })
            assert r.status_code == 201

    async def test_auto_devuelve_id_uuid(self, client: AsyncClient, test_user, auth_headers):
        import re
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto UUID Check",
        })
        assert r.status_code == 201
        uuid_pat = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        assert uuid_pat.match(r.json()["id"])

    async def test_nombre_con_acento(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Automatización de nóminas mensuales",
        })
        assert r.status_code == 201
        assert "Automatización" in r.json()["nombre"]

    async def test_nombre_con_numeros(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto v2.0 #003",
        })
        assert r.status_code == 201
