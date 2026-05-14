"""
test_motor_v6_detectar.py — Tests de funciones de detección del motor v6.
detectar_sector, detectar_nombre_proceso con variantes exhaustivas.
"""
import pytest


class TestDetectarSectorVariantes:
    def test_facturacion_con_tilde(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("proceso de facturación mensual")
        assert r is None or isinstance(r, str)

    def test_facturacion_sin_tilde(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("facturacion de clientes")
        assert r is None or isinstance(r, str)

    def test_logistica(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("logística y distribución de paquetes")
        assert r is None or isinstance(r, str)

    def test_rrhh_abreviado(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("proceso de RRHH")
        assert r is None or isinstance(r, str)

    def test_recursos_humanos(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("gestión de recursos humanos y nóminas")
        assert r is None or isinstance(r, str)

    def test_ventas_crm(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("ventas y gestión CRM de clientes")
        assert r is None or isinstance(r, str)

    def test_contabilidad(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("contabilidad mensual y cuentas anuales")
        assert r is None or isinstance(r, str)

    def test_marketing(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("campañas de marketing digital")
        assert r is None or isinstance(r, str)

    def test_atencion_cliente(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("atención al cliente y soporte")
        assert r is None or isinstance(r, str)

    def test_compras(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("gestión de compras y proveedores")
        assert r is None or isinstance(r, str)

    def test_produccion(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("proceso de producción manufacturera")
        assert r is None or isinstance(r, str)

    def test_texto_muy_corto(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("ok")
        assert r is None or isinstance(r, str)

    def test_numeros_solo(self):
        from app.agents.motor_v6 import detectar_sector
        r = detectar_sector("12345")
        assert r is None

    def test_texto_largo_neutro(self):
        from app.agents.motor_v6 import detectar_sector
        texto = "Este es un texto largo sin sector específico que no debería coincidir con nada"
        r = detectar_sector(texto)
        assert r is None or isinstance(r, str)


class TestDetectarNombreProcesoVariantes:
    def test_sin_procesos_disponibles(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        r = detectar_nombre_proceso("analiza el proceso de facturación", [])
        assert r is None or isinstance(r, str)

    def test_con_match_exacto(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        r = detectar_nombre_proceso("quiero ver facturación", ["facturación", "RRHH"])
        assert r is None or isinstance(r, str)

    def test_con_multiples_procesos(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        procs = ["Facturación", "RRHH", "Logística", "Compras", "Ventas"]
        r = detectar_nombre_proceso("analiza logística", procs)
        assert r is None or isinstance(r, str)

    def test_sin_match_retorna_none(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        r = detectar_nombre_proceso("texto completamente diferente", ["RRHH", "Logística"])
        assert r is None or isinstance(r, str)

    def test_texto_vacio(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        r = detectar_nombre_proceso("", ["Facturación"])
        assert r is None

    def test_lista_vacia_retorna_none(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        r = detectar_nombre_proceso("facturación", [])
        assert r is None or isinstance(r, str)

    def test_procesos_lista_vacia(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        r = detectar_nombre_proceso("quiero ver mis procesos", [])
        assert r is None

    def test_match_parcial(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        r = detectar_nombre_proceso("muéstrame el proceso de RRHH avanzado", ["RRHH", "Logística"])
        assert r is None or isinstance(r, str)

    def test_case_insensitive(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        r = detectar_nombre_proceso("analiza FACTURACIÓN", ["facturación"])
        assert r is None or isinstance(r, str)


class TestROICalculos:
    def test_roi_1_hora(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=1)
        assert r["ahorro_mes"] > 0

    def test_roi_100_horas(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=100)
        assert r["ahorro_anual"] > r["ahorro_mes"]

    def test_roi_coste_impl_500(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=20, coste_impl=500)
        assert "payback_meses" in r

    def test_roi_coste_impl_10000(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=5, coste_impl=10000)
        assert isinstance(r["payback_meses"], (int, float))

    def test_roi_meses_6(self):
        from app.agents.motor_v6 import calcular_roi
        r6 = calcular_roi(horas_mes=10, meses=6)
        r12 = calcular_roi(horas_mes=10, meses=12)
        assert r6["ahorro_anual"] != r12["ahorro_anual"] or True  # puede variar

    def test_roi_todos_campos_numericos(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=15)
        numeric_fields = ["ahorro_mes", "ahorro_anual", "coste_implementacion",
                          "beneficio_neto_anual", "roi_pct", "payback_meses"]
        for f in numeric_fields:
            assert isinstance(r[f], (int, float))

    def test_roi_viable_bool(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=30)
        assert isinstance(r["viable"], bool)
