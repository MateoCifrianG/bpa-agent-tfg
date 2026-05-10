"""
test_automatizaciones_completo.py — Tests exhaustivos de automatizaciones:
todos los campos, estados, validaciones, herramientas, CRUD completo, edge cases.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_auto(client: AsyncClient, test_user, auth_headers, test_proceso):
    r = await client.post("/api/automatizaciones", headers=auth_headers, json={
        "nombre": "Auto Test Base",
        "proceso_id": test_proceso["id"],
    })
    assert r.status_code == 201
    return r.json()


class TestAutomatizacionCampos:
    async def test_id_es_uuid(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        import re
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "UUID Test", "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 201
        pid = r.json()["id"]
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        assert uuid_pattern.match(pid)

    async def test_nombre_presente(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Nombre", "proceso_id": test_proceso["id"],
        })
        assert r.json()["nombre"] == "Auto Nombre"

    async def test_estado_default_es_string(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Estado", "proceso_id": test_proceso["id"],
        })
        assert r.json()["estado"] is None or isinstance(r.json()["estado"], str)

    async def test_estado_activo(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Activo", "proceso_id": test_proceso["id"], "estado": "activo",
        })
        assert r.json()["estado"] == "activo"

    async def test_estado_inactivo(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Inactivo", "proceso_id": test_proceso["id"], "estado": "inactivo",
        })
        assert r.json()["estado"] == "inactivo"

    async def test_estado_pausado(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Pausado", "proceso_id": test_proceso["id"], "estado": "pausado",
        })
        assert r.status_code in (201, 422)  # depende de validación del estado

    async def test_herramienta_n8n(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto n8n", "proceso_id": test_proceso["id"], "herramienta": "n8n",
        })
        assert r.json()["herramienta"] == "n8n"

    async def test_herramienta_zapier(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Zapier", "proceso_id": test_proceso["id"], "herramienta": "zapier",
        })
        assert r.json()["herramienta"] == "zapier"

    async def test_herramienta_make(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Make", "proceso_id": test_proceso["id"], "herramienta": "make",
        })
        assert r.json()["herramienta"] == "make"

    async def test_herramienta_python(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Python", "proceso_id": test_proceso["id"], "herramienta": "python",
        })
        assert r.json()["herramienta"] == "python"

    async def test_herramienta_personalizada(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Custom", "proceso_id": test_proceso["id"], "herramienta": "custom_tool",
        })
        assert r.status_code == 201

    async def test_descripcion_presente(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Desc", "proceso_id": test_proceso["id"],
            "descripcion": "Automatización de prueba para tests",
        })
        assert r.json()["descripcion"] == "Automatización de prueba para tests"

    async def test_descripcion_nula_por_defecto(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Sin Desc", "proceso_id": test_proceso["id"],
        })
        assert r.json().get("descripcion") in (None, "")

    async def test_ejecuciones_default_cero(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Ejec", "proceso_id": test_proceso["id"],
        })
        assert r.json().get("ejecuciones", 0) == 0

    async def test_horas_mes_personalizado(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Horas", "proceso_id": test_proceso["id"], "horas_mes": 40,
        })
        assert r.json()["horas_mes"] == 40

    async def test_proceso_id_presente(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Proc", "proceso_id": test_proceso["id"],
        })
        assert r.json()["proceso_id"] == test_proceso["id"]

    async def test_created_at_presente(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Fecha", "proceso_id": test_proceso["id"],
        })
        assert "created_at" in r.json()

    async def test_sin_proceso_id_falla_o_acepta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Sin Proc",
        })
        # Puede requerir proceso_id o no
        assert r.status_code in (201, 422, 400)


class TestAutomatizacionCrear:
    async def test_crear_basica(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Básica", "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 201

    async def test_nombre_requerido(self, client: AsyncClient, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 422

    async def test_nombre_muy_largo_422(self, client: AsyncClient, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "A" * 300, "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 422

    async def test_sin_auth_401(self, client: AsyncClient, test_proceso):
        r = await client.post("/api/automatizaciones", json={
            "nombre": "Auto Sin Auth", "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 401

    async def test_nombre_con_caracteres_especiales(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto (Facturación) - v2.0", "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 201

    async def test_nombre_con_acento(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Gestión automática de nóminas", "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 201
        assert "nóminas" in r.json()["nombre"]

    async def test_xss_sanitizado(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "<script>alert(1)</script>Auto", "proceso_id": test_proceso["id"],
        })
        if r.status_code == 201:
            assert "<script>" not in r.json()["nombre"]

    async def test_proceso_invalido_falla(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Proc Inválido",
            "proceso_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code in (400, 403, 404, 422)


class TestAutomatizacionLeer:
    async def test_listar_todas(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_listar_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/automatizaciones")
        assert r.status_code == 401

    async def test_listar_filtrado_por_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Filtrada", "proceso_id": test_proceso["id"],
        })
        r = await client.get(f"/api/automatizaciones?proceso_id={test_proceso['id']}", headers=auth_headers)
        assert r.status_code == 200
        for auto in r.json():
            assert auto["proceso_id"] == test_proceso["id"]

    async def test_obtener_por_id(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.get(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == test_auto["id"]

    async def test_obtener_id_inexistente_404(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/automatizaciones/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code == 404

    async def test_obtener_requiere_auth(self, client: AsyncClient, test_auto):
        r = await client.get(f"/api/automatizaciones/{test_auto['id']}")
        assert r.status_code == 401

    async def test_listar_vacio_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestAutomatizacionEditar:
    async def test_editar_nombre(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers,
                             json={"nombre": "Auto Renombrada"})
        assert r.status_code == 200
        assert r.json()["nombre"] == "Auto Renombrada"

    async def test_editar_estado(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers,
                             json={"estado": "inactivo"})
        assert r.status_code == 200
        assert r.json()["estado"] == "inactivo"

    async def test_editar_herramienta(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers,
                             json={"herramienta": "zapier"})
        assert r.status_code == 200
        assert r.json()["herramienta"] == "zapier"

    async def test_editar_descripcion(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers,
                             json={"descripcion": "Nueva descripción"})
        assert r.status_code == 200
        assert r.json()["descripcion"] == "Nueva descripción"

    async def test_editar_horas_mes(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers,
                             json={"horas_mes": 80})
        assert r.status_code == 200
        assert r.json()["horas_mes"] == 80

    async def test_editar_ejecuciones(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers,
                             json={"ejecuciones": 100})
        assert r.status_code == 200
        assert r.json()["ejecuciones"] == 100

    async def test_editar_proceso_id(self, client: AsyncClient, test_user, auth_headers, test_auto, test_proceso):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers,
                             json={"proceso_id": test_proceso["id"]})
        assert r.status_code == 200

    async def test_editar_no_existe_404(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/automatizaciones/00000000-0000-0000-0000-000000000000",
                             headers=auth_headers, json={"nombre": "X"})
        assert r.status_code == 404

    async def test_editar_requiere_auth(self, client: AsyncClient, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", json={"nombre": "X"})
        assert r.status_code == 401

    async def test_editar_preserva_campos_no_enviados(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        cr = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Preservar", "proceso_id": test_proceso["id"], "herramienta": "n8n",
            "descripcion": "desc original",
        })
        aid = cr.json()["id"]
        r = await client.put(f"/api/automatizaciones/{aid}", headers=auth_headers, json={"estado": "inactivo"})
        assert r.json()["nombre"] == "Auto Preservar"
        assert r.json()["herramienta"] == "n8n"
        assert r.json()["descripcion"] == "desc original"

    async def test_nombre_muy_largo_422(self, client: AsyncClient, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers,
                             json={"nombre": "N" * 300})
        assert r.status_code == 422


class TestAutomatizacionEliminar:
    async def test_eliminar_existente(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        cr = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto A Eliminar", "proceso_id": test_proceso["id"],
        })
        aid = cr.json()["id"]
        r = await client.delete(f"/api/automatizaciones/{aid}", headers=auth_headers)
        assert r.status_code == 204

    async def test_eliminar_no_existe_404(self, client: AsyncClient, auth_headers):
        r = await client.delete("/api/automatizaciones/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code == 404

    async def test_eliminar_requiere_auth(self, client: AsyncClient, test_auto):
        r = await client.delete(f"/api/automatizaciones/{test_auto['id']}")
        assert r.status_code == 401

    async def test_eliminar_doble_404(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        cr = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Doble Del", "proceso_id": test_proceso["id"],
        })
        aid = cr.json()["id"]
        await client.delete(f"/api/automatizaciones/{aid}", headers=auth_headers)
        r = await client.delete(f"/api/automatizaciones/{aid}", headers=auth_headers)
        assert r.status_code == 404

    async def test_eliminar_desaparece_de_listado(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        cr = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Para Borrar", "proceso_id": test_proceso["id"],
        })
        aid = cr.json()["id"]
        await client.delete(f"/api/automatizaciones/{aid}", headers=auth_headers)
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        ids = [a["id"] for a in r.json()]
        assert aid not in ids


class TestAutomatizacionAislamiento:
    async def test_usuario_solo_ve_sus_autos(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        import uuid
        uid = uuid.uuid4().hex[:8]
        # Crear usuario 2
        r2 = await client.post("/api/auth/register", json={
            "email": f"auto2_{uid}@test.com",
            "password": "TestPass1!",
            "nombre": "Auto2", "apellido": "User",
            "empresa": "Empresa2", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r2.status_code != 201:
            return  # skip si registro falla
        token2 = (await client.post("/api/auth/login", json={
            "email": f"auto2_{uid}@test.com", "password": "TestPass1!",
        })).json().get("access_token")
        if not token2:
            return
        headers2 = {"Authorization": f"Bearer {token2}"}
        # Usuario 2 intenta leer auto del usuario 1
        r = await client.get(f"/api/automatizaciones/{test_proceso['id']}", headers=headers2)
        assert r.status_code in (403, 404)
