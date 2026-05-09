"""
Seed script — popula la BD con datos de prueba reales.
Ejecutar: python seed.py
"""
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal, create_tables
from app.auth.jwt import hash_password
from app.models.user import User
from app.models.empresa import Empresa
from app.models.proceso import Proceso
from app.models.automatizacion import Automatizacion
from app.models.kpi import KPI


SEED_DATA = [
    {
        "user": {
            "email": "admin@bpa.com",
            "password": "Admin1234!",
            "nombre": "Admin",
            "apellido": "BPA",
            "role": "admin",
            "plan": "enterprise",
            "ciudad": "Bilbao",
        },
        "empresa": {
            "nombre": "BPA-Agent (Admin)",
            "sector": "Tecnología",
            "empleados": 10,
            "ciudad": "Bilbao",
            "descripcion": "Cuenta de administración del sistema.",
        },
        "procesos": [],
        "automatizaciones": [],
        "kpis": [],
    },
    {
        "user": {
            "email": "operaciones@eroski.es",
            "password": "Eroski2026!",
            "nombre": "Itziar",
            "apellido": "Uribe",
            "role": "user",
            "plan": "pro",
            "ciudad": "Elorrio",
        },
        "empresa": {
            "nombre": "Eroski S. Coop.",
            "sector": "Retail / Distribución",
            "empleados": 32000,
            "ciudad": "Elorrio (Bizkaia)",
            "descripcion": "Cooperativa de distribución y retail con presencia en toda España.",
        },
        "procesos": [
            {"nombre": "Gestión de pedidos a proveedores", "descripcion": "Proceso de generación y seguimiento de órdenes de compra a más de 800 proveedores nacionales.", "responsable": "Dept. Compras", "frecuencia": "diario", "duracion_h": 120, "score": 34, "estado": "critico", "notas": "Alto volumen manual, muchos errores de duplicado."},
            {"nombre": "Cierre contable mensual", "descripcion": "Conciliación de cuentas, facturas y extractos bancarios de las 250 tiendas.", "responsable": "Dept. Finanzas", "frecuencia": "mensual", "duracion_h": 80, "score": 51, "estado": "analizado", "notas": "Proceso muy largo, 12 personas involucradas."},
            {"nombre": "Generación de informes de ventas", "descripcion": "Reporting semanal de ventas por categoría, región y tienda.", "responsable": "Dirección Comercial", "frecuencia": "semanal", "duracion_h": 24, "score": 72, "estado": "optimizado", "notas": "Parcialmente automatizado con macros Excel."},
            {"nombre": "Onboarding de nuevos empleados", "descripcion": "Alta en sistemas, asignación de uniformes, formación inicial y firma de contratos.", "responsable": "RRHH", "frecuencia": "mensual", "duracion_h": 40, "score": 45, "estado": "analizado", "notas": ""},
            {"nombre": "Control de inventario en tienda", "descripcion": "Recuento semanal de stock, gestión de mermas y roturas.", "responsable": "Responsable de tienda", "frecuencia": "semanal", "duracion_h": 60, "score": 28, "estado": "critico", "notas": "Gran volumen de incidencias por diferencias de inventario."},
        ],
        "automatizaciones": [
            {"nombre": "Auto-pedido a proveedores", "descripcion": "Detecta stock mínimo y genera orden de compra en SAP automáticamente.", "herramienta": "SAP + n8n", "estado": "activa", "ejecuciones": 1240, "horas_mes": 80},
            {"nombre": "Envío informe ventas semanal", "descripcion": "Extrae datos del DWH y envía PDF por email al equipo directivo.", "herramienta": "Python + Gmail", "estado": "activa", "ejecuciones": 52, "horas_mes": 18},
            {"nombre": "Alta empleados en AD", "descripcion": "Crea cuenta de usuario en Active Directory y envía credenciales por email.", "herramienta": "PowerShell + Microsoft Graph", "estado": "pendiente", "ejecuciones": 0, "horas_mes": 15},
        ],
        "kpis": [
            {"nombre": "Tiempo medio pedido-recepción", "valor": "3.2 días", "objetivo": "2 días", "unidad": "días", "tendencia": "down", "categoria": "tiempo"},
            {"nombre": "Horas/mes ahorradas con IA", "valor": "98h", "objetivo": "150h", "unidad": "horas", "tendencia": "up", "categoria": "tiempo"},
            {"nombre": "Coste operativo mensual", "valor": "€ 48.200", "objetivo": "€ 40.000", "unidad": "euros", "tendencia": "down", "categoria": "coste"},
            {"nombre": "Errores en pedidos (%)", "valor": "6.4%", "objetivo": "< 2%", "unidad": "%", "tendencia": "down", "categoria": "calidad"},
            {"nombre": "Procesos digitalizados", "valor": "3 / 5", "objetivo": "5 / 5", "unidad": "procesos", "tendencia": "up", "categoria": "volumen"},
        ],
    },
    {
        "user": {
            "email": "digitalizacion@mondragon.edu",
            "password": "Mondragon2026!",
            "nombre": "Unai",
            "apellido": "Etxebarria",
            "role": "user",
            "plan": "pro",
            "ciudad": "Mondragón",
        },
        "empresa": {
            "nombre": "Mondragon Unibertsitatea",
            "sector": "Educación Superior",
            "empleados": 850,
            "ciudad": "Mondragón (Gipuzkoa)",
            "descripcion": "Universidad cooperativa con facultades de Empresariales, Ingeniería, Humanidades y Gastronomía.",
        },
        "procesos": [
            {"nombre": "Matriculación de alumnos", "descripcion": "Proceso de matrícula anual: validación documentación, asignación de grupos, cobro de tasas.", "responsable": "Secretaría Académica", "frecuencia": "anual", "duracion_h": 200, "score": 41, "estado": "analizado", "notas": "Pico de trabajo enorme en septiembre."},
            {"nombre": "Gestión de prácticas en empresa", "descripcion": "Coordinación y seguimiento de 400+ convenios de prácticas curriculares.", "responsable": "Oficina de Empleo", "frecuencia": "mensual", "duracion_h": 60, "score": 38, "estado": "critico", "notas": "Seguimiento manual en hojas de cálculo."},
            {"nombre": "Publicación de materiales en Moodle", "descripcion": "Subida de apuntes, videos y actividades por parte del profesorado.", "responsable": "Profesorado", "frecuencia": "semanal", "duracion_h": 90, "score": 65, "estado": "analizado", "notas": ""},
            {"nombre": "Generación de actas y certificados", "descripcion": "Emisión de actas de calificaciones y certificados académicos oficiales.", "responsable": "Secretaría", "frecuencia": "mensual", "duracion_h": 30, "score": 55, "estado": "analizado", "notas": ""},
        ],
        "automatizaciones": [
            {"nombre": "Envío automático credenciales Moodle", "descripcion": "Al confirmar matrícula, genera y envía usuario/contraseña de Moodle al nuevo alumno.", "herramienta": "Python + Moodle API + SMTP", "estado": "activa", "ejecuciones": 720, "horas_mes": 40},
            {"nombre": "Recordatorio seguimiento prácticas", "descripcion": "Envía email semanal al tutor y al alumno con checklist de seguimiento.", "herramienta": "n8n + Gmail", "estado": "activa", "ejecuciones": 1600, "horas_mes": 20},
            {"nombre": "Generación de certificados PDF", "descripcion": "Genera PDF firmado digitalmente con datos del alumno al solicitar certificado.", "herramienta": "Python + ReportLab", "estado": "pendiente", "ejecuciones": 0, "horas_mes": 25},
        ],
        "kpis": [
            {"nombre": "Tiempo medio de matriculación", "valor": "4.5 días", "objetivo": "1 día", "unidad": "días", "tendencia": "flat", "categoria": "tiempo"},
            {"nombre": "Satisfacción alumno (encuesta)", "valor": "7.8 / 10", "objetivo": "9 / 10", "unidad": "puntos", "tendencia": "up", "categoria": "calidad"},
            {"nombre": "Horas/mes ahorradas con IA", "valor": "60h", "objetivo": "120h", "unidad": "horas", "tendencia": "up", "categoria": "tiempo"},
            {"nombre": "Convenios prácticas activos", "valor": "412", "objetivo": "500", "unidad": "convenios", "tendencia": "up", "categoria": "volumen"},
        ],
    },
    {
        "user": {
            "email": "transformacion@naturgy.com",
            "password": "Naturgy2026!",
            "nombre": "Mónica",
            "apellido": "Serrano",
            "role": "user",
            "plan": "pro",
            "ciudad": "Madrid",
        },
        "empresa": {
            "nombre": "Naturgy Energy Group",
            "sector": "Energía / Utilities",
            "empleados": 11000,
            "ciudad": "Madrid",
            "descripcion": "Multinacional energética presente en 20 países, distribución y comercialización de gas y electricidad.",
        },
        "procesos": [
            {"nombre": "Alta de nuevos suministros", "descripcion": "Tramitación de solicitudes de alta de gas/electricidad: verificación, inspección, activación.", "responsable": "Dpto. Comercial", "frecuencia": "diario", "duracion_h": 150, "score": 29, "estado": "critico", "notas": "Alta tasa de abandono del cliente por tiempos de espera."},
            {"nombre": "Facturación mensual", "descripcion": "Generación y envío de 2M+ facturas mensuales a clientes residenciales y empresas.", "responsable": "Dpto. Facturación", "frecuencia": "mensual", "duracion_h": 300, "score": 58, "estado": "analizado", "notas": ""},
            {"nombre": "Atención a reclamaciones", "descripcion": "Gestión de incidencias, reclamaciones de facturación y cortes de suministro.", "responsable": "Contact Center", "frecuencia": "diario", "duracion_h": 400, "score": 35, "estado": "critico", "notas": "70% son consultas repetitivas que podrían automatizarse."},
            {"nombre": "Reporting regulatorio a CNMC", "descripcion": "Elaboración y envío de informes periódicos al regulador energético.", "responsable": "Dpto. Regulación", "frecuencia": "mensual", "duracion_h": 50, "score": 60, "estado": "analizado", "notas": ""},
        ],
        "automatizaciones": [
            {"nombre": "Chatbot reclamaciones 24/7", "descripcion": "Responde automáticamente a las 50 consultas más frecuentes de clientes.", "herramienta": "Claude API + Zendesk", "estado": "activa", "ejecuciones": 8900, "horas_mes": 200},
            {"nombre": "Pipeline facturación automática", "descripcion": "Extrae consumos del sistema de medición, genera facturas y las envía por email/postal.", "herramienta": "SAP IS-U + Python", "estado": "activa", "ejecuciones": 2100000, "horas_mes": 250},
            {"nombre": "Auto-reporting CNMC", "descripcion": "Recoge datos de los sistemas operacionales y rellena los templates del regulador.", "herramienta": "Python + Selenium", "estado": "pausada", "ejecuciones": 8, "horas_mes": 35},
        ],
        "kpis": [
            {"nombre": "Tiempo resolución reclamación", "valor": "5.1 días", "objetivo": "2 días", "unidad": "días", "tendencia": "down", "categoria": "tiempo"},
            {"nombre": "Horas/mes ahorradas con IA", "valor": "450h", "objetivo": "600h", "unidad": "horas", "tendencia": "up", "categoria": "tiempo"},
            {"nombre": "Tasa resolución autom. chatbot", "valor": "64%", "objetivo": "80%", "unidad": "%", "tendencia": "up", "categoria": "calidad"},
            {"nombre": "Coste atención al cliente/mes", "valor": "€ 320.000", "objetivo": "€ 200.000", "unidad": "euros", "tendencia": "down", "categoria": "coste"},
            {"nombre": "NPS clientes", "valor": "38", "objetivo": "55", "unidad": "puntos", "tendencia": "up", "categoria": "calidad"},
        ],
    },
    {
        "user": {
            "email": "operaciones@ikea.es",
            "password": "Ikea2026!",
            "nombre": "Lars",
            "apellido": "Andersen",
            "role": "user",
            "plan": "free",
            "ciudad": "Madrid",
        },
        "empresa": {
            "nombre": "IKEA España",
            "sector": "Retail / Muebles y Hogar",
            "empleados": 7500,
            "ciudad": "Madrid",
            "descripcion": "Subsidiaria española de IKEA con 20 tiendas y plataforma ecommerce.",
        },
        "procesos": [
            {"nombre": "Gestión de devoluciones", "descripcion": "Proceso de recepción, inspección y reembolso/cambio de productos devueltos.", "responsable": "Customer Service", "frecuencia": "diario", "duracion_h": 80, "score": 48, "estado": "analizado", "notas": ""},
            {"nombre": "Planificación y reposición de almacén", "descripcion": "Cálculo de necesidades de stock, órdenes de reposición inter-almacén y a proveedor.", "responsable": "Supply Chain", "frecuencia": "semanal", "duracion_h": 60, "score": 71, "estado": "optimizado", "notas": ""},
            {"nombre": "Publicación de ofertas en web", "descripcion": "Alta de productos, precios y ofertas en la plataforma ecommerce IKEA.es.", "responsable": "E-commerce", "frecuencia": "semanal", "duracion_h": 20, "score": 66, "estado": "analizado", "notas": ""},
        ],
        "automatizaciones": [
            {"nombre": "Bot clasificación devoluciones", "descripcion": "Clasifica automáticamente la causa de devolución según descripción del cliente.", "herramienta": "Claude API", "estado": "pendiente", "ejecuciones": 0, "horas_mes": 30},
        ],
        "kpis": [
            {"nombre": "Tiempo medio devolución", "valor": "2.8 días", "objetivo": "1 día", "unidad": "días", "tendencia": "flat", "categoria": "tiempo"},
            {"nombre": "Coste devoluciones/mes", "valor": "€ 85.000", "objetivo": "€ 60.000", "unidad": "euros", "tendencia": "down", "categoria": "coste"},
            {"nombre": "Satisfacción post-compra", "valor": "8.1 / 10", "objetivo": "9 / 10", "unidad": "puntos", "tendencia": "up", "categoria": "calidad"},
        ],
    },
    {
        "user": {
            "email": "admin@clinicaNavarro.es",
            "password": "Clinica2026!",
            "nombre": "Carmen",
            "apellido": "Navarro",
            "role": "user",
            "plan": "free",
            "ciudad": "Pamplona",
        },
        "empresa": {
            "nombre": "Clínica Navarro",
            "sector": "Salud / Clínica privada",
            "empleados": 65,
            "ciudad": "Pamplona (Navarra)",
            "descripcion": "Clínica privada de especialidades médicas con más de 30 años de historia en Navarra.",
        },
        "procesos": [
            {"nombre": "Gestión de citas médicas", "descripcion": "Recepción de llamadas, asignación de hueco en agenda del especialista, confirmación y recordatorio.", "responsable": "Administración", "frecuencia": "diario", "duracion_h": 50, "score": 42, "estado": "analizado", "notas": "80% de citas se gestionan aún por teléfono."},
            {"nombre": "Facturación a aseguradoras", "descripcion": "Elaboración y envío de facturas a mutuas y compañías de seguros.", "responsable": "Contabilidad", "frecuencia": "mensual", "duracion_h": 35, "score": 50, "estado": "analizado", "notas": ""},
            {"nombre": "Historia clínica electrónica", "descripcion": "Actualización de la HCE tras cada consulta, informes y derivaciones.", "responsable": "Personal médico", "frecuencia": "diario", "duracion_h": 90, "score": 62, "estado": "analizado", "notas": ""},
        ],
        "automatizaciones": [
            {"nombre": "Recordatorio automático de citas", "descripcion": "Envía SMS y email 24h antes de la cita al paciente.", "herramienta": "n8n + Twilio + SMTP", "estado": "activa", "ejecuciones": 3200, "horas_mes": 20},
        ],
        "kpis": [
            {"nombre": "Tasa de no-presentación (no-show)", "valor": "12%", "objetivo": "< 5%", "unidad": "%", "tendencia": "down", "categoria": "calidad"},
            {"nombre": "Tiempo medio gestión cita", "valor": "8 min", "objetivo": "2 min", "unidad": "minutos", "tendencia": "flat", "categoria": "tiempo"},
            {"nombre": "Horas/mes ahorradas con IA", "valor": "20h", "objetivo": "50h", "unidad": "horas", "tendencia": "up", "categoria": "tiempo"},
            {"nombre": "Satisfacción paciente", "valor": "8.6 / 10", "objetivo": "9.5 / 10", "unidad": "puntos", "tendencia": "up", "categoria": "calidad"},
        ],
    },
]


async def seed():
    await create_tables()
    async with AsyncSessionLocal() as db:
        # Limpiar datos existentes
        await db.execute(text("DELETE FROM kpis"))
        await db.execute(text("DELETE FROM automatizaciones"))
        await db.execute(text("DELETE FROM procesos"))
        await db.execute(text("DELETE FROM conversaciones"))
        await db.execute(text("DELETE FROM empresas"))
        await db.execute(text("DELETE FROM users"))
        await db.commit()
        print("[OK] BD limpiada")

        for entry in SEED_DATA:
            u_data = entry["user"]
            user = User(
                email=u_data["email"],
                hashed_password=hash_password(u_data["password"]),
                nombre=u_data["nombre"],
                apellido=u_data["apellido"],
                role=u_data["role"],
                plan=u_data["plan"],
                ciudad=u_data["ciudad"],
            )
            db.add(user)
            await db.flush()

            e_data = entry["empresa"]
            empresa = Empresa(
                user_id=user.id,
                nombre=e_data["nombre"],
                sector=e_data["sector"],
                empleados=e_data["empleados"],
                ciudad=e_data["ciudad"],
                descripcion=e_data["descripcion"],
            )
            db.add(empresa)
            await db.flush()

            proceso_map = {}
            for p_data in entry["procesos"]:
                proceso = Proceso(empresa_id=empresa.id, **p_data)
                db.add(proceso)
                await db.flush()
                proceso_map[p_data["nombre"]] = proceso.id

            for a_data in entry["automatizaciones"]:
                auto = Automatizacion(empresa_id=empresa.id, **a_data)
                db.add(auto)

            for k_data in entry["kpis"]:
                kpi = KPI(empresa_id=empresa.id, **k_data)
                db.add(kpi)

            await db.commit()
            print(f"[OK] {u_data['email']}  --  {e_data['nombre']}")

    print("\nSeed completado. Base de datos lista.")
    print("\nCredenciales:")
    print("  admin@bpa.com         /  Admin1234!")
    print("  operaciones@eroski.es /  Eroski2026!")
    print("  digitalizacion@mondragon.edu / Mondragon2026!")
    print("  transformacion@naturgy.com   / Naturgy2026!")
    print("  operaciones@ikea.es          / Ikea2026!")
    print("  admin@clinicaNavarro.es      / Clinica2026!")


if __name__ == "__main__":
    asyncio.run(seed())
