"""
motor_v6_kb.py — Base de conocimiento BPA-Agent v6
Conocimiento experto en BPA: sectores, KPIs, automatizaciones,
benchmarks, ROI, patrones de proceso y respuestas naturales.
"""

# ──────────────────────────────────────────────────────────────────────────────
# SECTORES — conocimiento profundo por industria
# ──────────────────────────────────────────────────────────────────────────────

SECTORES: dict[str, dict] = {
    "logística": {
        "aliases": ["logistica", "supply chain", "cadena de suministro", "transporte", "distribución", "almacén", "almacen", "warehouse"],
        "procesos_tipicos": [
            "Gestión de pedidos", "Control de inventario", "Planificación de rutas",
            "Recepción de mercancía", "Expedición y envíos", "Devoluciones",
            "Gestión de proveedores", "Trazabilidad de envíos",
        ],
        "kpis": {
            "Tiempo de ciclo de pedido": {"unidad": "horas", "benchmark_bueno": 24, "benchmark_malo": 72, "descripcion": "Desde que entra el pedido hasta que sale del almacén"},
            "Tasa de entrega a tiempo": {"unidad": "%", "benchmark_bueno": 97, "benchmark_malo": 85, "descripcion": "Pedidos entregados en la fecha prometida"},
            "Precisión de inventario": {"unidad": "%", "benchmark_bueno": 99.5, "benchmark_malo": 95, "descripcion": "Stock real vs stock en sistema"},
            "Coste por envío": {"unidad": "€", "benchmark_bueno": 4.5, "benchmark_malo": 12, "descripcion": "Coste total dividido entre número de envíos"},
            "Tasa de devoluciones": {"unidad": "%", "benchmark_bueno": 2, "benchmark_malo": 8, "descripcion": "Porcentaje de pedidos devueltos"},
            "Tiempo de descarga": {"unidad": "minutos", "benchmark_bueno": 30, "benchmark_malo": 90, "descripcion": "Tiempo medio para descargar un camión"},
            "Fill rate": {"unidad": "%", "benchmark_bueno": 98, "benchmark_malo": 90, "descripcion": "Pedidos servidos completos sin rotura de stock"},
            "Rotación de inventario": {"unidad": "veces/año", "benchmark_bueno": 12, "benchmark_malo": 4, "descripcion": "Cuántas veces se renueva el inventario al año"},
        },
        "automatizaciones": [
            "Notificación automática de estado de pedido al cliente",
            "Alerta de stock mínimo y reorden automático",
            "Generación automática de albaranes y etiquetas",
            "Integración ERP con transportista para tracking",
            "Informe diario de expediciones por email",
            "Alerta de retraso en entrega con escalado automático",
        ],
        "puntos_dolor": [
            "Roturas de stock frecuentes",
            "Falta de visibilidad en tiempo real de envíos",
            "Errores en picking manual",
            "Retrasos en notificación al cliente",
        ],
        "roi_horas_mes": 35,
    },
    "recursos humanos": {
        "aliases": ["rrhh", "hr", "recursos humanos", "people", "talento", "personal"],
        "procesos_tipicos": [
            "Selección y reclutamiento", "Onboarding de empleados", "Gestión de nóminas",
            "Control de vacaciones y ausencias", "Evaluación del desempeño",
            "Formación y desarrollo", "Offboarding", "Gestión de documentación laboral",
        ],
        "kpis": {
            "Tiempo de contratación": {"unidad": "días", "benchmark_bueno": 21, "benchmark_malo": 45, "descripcion": "Días desde apertura de vacante hasta incorporación"},
            "Tasa de rotación": {"unidad": "%", "benchmark_bueno": 8, "benchmark_malo": 25, "descripcion": "Empleados que abandonan la empresa en un año"},
            "Coste por contratación": {"unidad": "€", "benchmark_bueno": 2500, "benchmark_malo": 8000, "descripcion": "Coste total del proceso de selección"},
            "Satisfacción empleados (eNPS)": {"unidad": "puntos", "benchmark_bueno": 40, "benchmark_malo": 0, "descripcion": "Employee Net Promoter Score"},
            "Tiempo de onboarding": {"unidad": "días", "benchmark_bueno": 14, "benchmark_malo": 60, "descripcion": "Días hasta que el empleado es totalmente productivo"},
            "Absentismo": {"unidad": "%", "benchmark_bueno": 2, "benchmark_malo": 6, "descripcion": "Porcentaje de horas perdidas por ausencias"},
            "Ratio formación": {"unidad": "horas/empleado/año", "benchmark_bueno": 40, "benchmark_malo": 10, "descripcion": "Horas de formación por empleado al año"},
        },
        "automatizaciones": [
            "Envío automático de documentos de bienvenida al nuevo empleado",
            "Recordatorio de evaluaciones de desempeño",
            "Notificación de vacaciones aprobadas/rechazadas",
            "Generación automática de contratos desde plantilla",
            "Alerta de vencimiento de contratos temporales",
            "Informe mensual de absentismo automático",
            "Encuesta de satisfacción automática tras 90 días",
        ],
        "puntos_dolor": [
            "Procesos de onboarding manuales y largos",
            "Alta carga administrativa en nóminas",
            "Falta de seguimiento del desempeño",
            "Comunicación interna ineficiente",
        ],
        "roi_horas_mes": 28,
    },
    "finanzas": {
        "aliases": ["finanzas", "finance", "contabilidad", "tesorería", "tesoreria", "cuentas", "facturación", "facturacion"],
        "procesos_tipicos": [
            "Facturación a clientes", "Gestión de cobros", "Pago a proveedores",
            "Cierre contable mensual", "Conciliación bancaria", "Gestión de gastos",
            "Reporting financiero", "Auditoría interna", "Presupuestación",
        ],
        "kpis": {
            "DSO (días de cobro)": {"unidad": "días", "benchmark_bueno": 30, "benchmark_malo": 60, "descripcion": "Días de media que tarda en cobrarse una factura"},
            "DPO (días de pago)": {"unidad": "días", "benchmark_bueno": 45, "benchmark_malo": 15, "descripcion": "Días de media que se tarda en pagar a proveedores"},
            "Tasa de error en facturas": {"unidad": "%", "benchmark_bueno": 0.5, "benchmark_malo": 5, "descripcion": "Facturas con errores sobre el total emitido"},
            "Tiempo de cierre mensual": {"unidad": "días", "benchmark_bueno": 3, "benchmark_malo": 10, "descripcion": "Días para cerrar contablemente un mes"},
            "Cash conversion cycle": {"unidad": "días", "benchmark_bueno": 20, "benchmark_malo": 60, "descripcion": "Ciclo de conversión de efectivo"},
            "Coste proceso AP": {"unidad": "€/factura", "benchmark_bueno": 3, "benchmark_malo": 15, "descripcion": "Coste de procesar cada factura de proveedor"},
            "Facturas procesadas/FTE": {"unidad": "facturas/mes", "benchmark_bueno": 800, "benchmark_malo": 200, "descripcion": "Facturas procesadas por persona al mes"},
        },
        "automatizaciones": [
            "Envío automático de facturas y recordatorios de cobro",
            "Conciliación bancaria automática",
            "Generación de informes financieros mensuales",
            "Alerta de facturas vencidas sin cobrar",
            "Extracción automática de datos de facturas (OCR)",
            "Aprobación automática de gastos bajo umbral",
            "Notificación de anomalías en gastos",
        ],
        "puntos_dolor": [
            "Cobros tardíos que afectan al cash flow",
            "Cierre contable lento y manual",
            "Errores en facturación manual",
            "Falta de visibilidad del estado de cobros",
        ],
        "roi_horas_mes": 42,
    },
    "ventas": {
        "aliases": ["ventas", "sales", "comercial", "crm", "clientes"],
        "procesos_tipicos": [
            "Gestión del pipeline de ventas", "Cualificación de leads",
            "Preparación de propuestas", "Seguimiento de oportunidades",
            "Gestión de contratos", "Reporting de ventas", "Atención postventa",
        ],
        "kpis": {
            "Tasa de conversión": {"unidad": "%", "benchmark_bueno": 25, "benchmark_malo": 8, "descripcion": "Porcentaje de leads que se convierten en clientes"},
            "Ciclo de venta": {"unidad": "días", "benchmark_bueno": 30, "benchmark_malo": 90, "descripcion": "Días desde primer contacto hasta cierre"},
            "Ticket medio": {"unidad": "€", "benchmark_bueno": None, "benchmark_malo": None, "descripcion": "Valor medio por venta"},
            "Coste de adquisición (CAC)": {"unidad": "€", "benchmark_bueno": None, "benchmark_malo": None, "descripcion": "Coste de conseguir un nuevo cliente"},
            "Churn rate": {"unidad": "%", "benchmark_bueno": 5, "benchmark_malo": 20, "descripcion": "Tasa de abandono de clientes"},
            "NPS clientes": {"unidad": "puntos", "benchmark_bueno": 50, "benchmark_malo": 10, "descripcion": "Net Promoter Score de clientes"},
            "Forecast accuracy": {"unidad": "%", "benchmark_bueno": 90, "benchmark_malo": 70, "descripcion": "Precisión en la previsión de ventas"},
        },
        "automatizaciones": [
            "Seguimiento automático de oportunidades sin actividad",
            "Email de bienvenida y nurturing a nuevos leads",
            "Recordatorio automático de renovaciones",
            "Generación automática de propuestas desde plantilla",
            "Reporte semanal de pipeline al equipo comercial",
            "Alerta de deal en riesgo de perderse",
        ],
        "puntos_dolor": [
            "Seguimiento manual e inconsistente de oportunidades",
            "Pérdida de leads por falta de respuesta rápida",
            "Reporting manual que consume mucho tiempo",
            "Falta de visibilidad del pipeline en tiempo real",
        ],
        "roi_horas_mes": 25,
    },
    "atención al cliente": {
        "aliases": ["atención al cliente", "atencion al cliente", "soporte", "support", "customer service", "helpdesk", "servicio al cliente"],
        "procesos_tipicos": [
            "Gestión de tickets", "Resolución de reclamaciones", "Atención multicanal",
            "Escalado de incidencias", "FAQ y base de conocimiento", "Satisfacción post-resolución",
        ],
        "kpis": {
            "CSAT": {"unidad": "%", "benchmark_bueno": 90, "benchmark_malo": 70, "descripcion": "Satisfacción del cliente tras la interacción"},
            "FCR (resolución en primer contacto)": {"unidad": "%", "benchmark_bueno": 75, "benchmark_malo": 50, "descripcion": "Tickets resueltos sin necesidad de escalado"},
            "Tiempo de primera respuesta": {"unidad": "horas", "benchmark_bueno": 1, "benchmark_malo": 8, "descripcion": "Tiempo hasta que el cliente recibe primera respuesta"},
            "Tiempo de resolución": {"unidad": "horas", "benchmark_bueno": 4, "benchmark_malo": 24, "descripcion": "Tiempo total hasta cerrar el ticket"},
            "Tickets por agente/día": {"unidad": "tickets", "benchmark_bueno": 25, "benchmark_malo": 8, "descripcion": "Productividad del agente de soporte"},
            "Tasa de escalado": {"unidad": "%", "benchmark_bueno": 10, "benchmark_malo": 35, "descripcion": "Porcentaje de tickets que requieren escalado"},
        },
        "automatizaciones": [
            "Respuesta automática de acuse de recibo al cliente",
            "Clasificación y asignación automática de tickets por urgencia",
            "Encuesta de satisfacción automática al cerrar ticket",
            "Escalado automático si ticket lleva >X horas sin respuesta",
            "Respuesta automática a preguntas frecuentes (FAQ bot)",
            "Reporte semanal de métricas de soporte",
        ],
        "puntos_dolor": [
            "Tiempos de respuesta lentos que generan insatisfacción",
            "Falta de trazabilidad de reclamaciones",
            "Sobrecarga del equipo en picos de demanda",
            "Repetición de las mismas preguntas frecuentes",
        ],
        "roi_horas_mes": 30,
    },
    "marketing": {
        "aliases": ["marketing", "comunicación", "comunicacion", "publicidad", "publicitar", "redes sociales", "contenido", "campaña", "campañas", "campana", "campanas"],
        "procesos_tipicos": [
            "Gestión de campañas", "Creación de contenido", "Email marketing",
            "Gestión de redes sociales", "Análisis de métricas", "Generación de leads",
            "SEO/SEM", "Eventos y webinars",
        ],
        "kpis": {
            "ROI de campaña": {"unidad": "%", "benchmark_bueno": 300, "benchmark_malo": 50, "descripcion": "Retorno sobre la inversión en marketing"},
            "Tasa de apertura email": {"unidad": "%", "benchmark_bueno": 25, "benchmark_malo": 10, "descripcion": "Porcentaje de emails abiertos"},
            "CTR": {"unidad": "%", "benchmark_bueno": 3, "benchmark_malo": 0.5, "descripcion": "Click-through rate en campañas"},
            "CPL (coste por lead)": {"unidad": "€", "benchmark_bueno": 20, "benchmark_malo": 100, "descripcion": "Coste de conseguir un lead cualificado"},
            "Engagement rate": {"unidad": "%", "benchmark_bueno": 5, "benchmark_malo": 1, "descripcion": "Interacciones sobre alcance en redes sociales"},
            "Tasa de conversión web": {"unidad": "%", "benchmark_bueno": 3, "benchmark_malo": 0.5, "descripcion": "Visitantes web que realizan una acción deseada"},
        },
        "automatizaciones": [
            "Publicación automática en redes sociales",
            "Secuencias de email nurturing automáticas",
            "Reporte semanal de métricas de redes sociales",
            "Alerta de mención de marca en redes",
            "Segmentación automática de leads por comportamiento",
        ],
        "puntos_dolor": [
            "Mucho tiempo en tareas repetitivas de publicación",
            "Falta de personalización en comunicaciones masivas",
            "Dificultad para medir ROI de acciones",
        ],
        "roi_horas_mes": 22,
    },
    "tecnología": {
        "aliases": ["tecnología", "tecnologia", "it", "ti", "tecnologías de la información", "informática", "informatica", "software", "desarrollo"],
        "procesos_tipicos": [
            "Gestión de incidencias IT", "Despliegue de software", "Monitorización de sistemas",
            "Gestión de accesos y usuarios", "Backup y recuperación", "Gestión de proyectos tech",
            "Code review y QA", "Gestión de licencias",
        ],
        "kpis": {
            "MTTR (tiempo de recuperación)": {"unidad": "horas", "benchmark_bueno": 1, "benchmark_malo": 8, "descripcion": "Tiempo medio para restaurar un servicio caído"},
            "MTBF (tiempo entre fallos)": {"unidad": "días", "benchmark_bueno": 90, "benchmark_malo": 15, "descripcion": "Tiempo medio entre incidencias"},
            "Uptime de sistemas": {"unidad": "%", "benchmark_bueno": 99.9, "benchmark_malo": 98, "descripcion": "Disponibilidad de los sistemas críticos"},
            "Tiempo de despliegue": {"unidad": "horas", "benchmark_bueno": 2, "benchmark_malo": 24, "descripcion": "Tiempo para desplegar una nueva versión"},
            "Cobertura de tests": {"unidad": "%", "benchmark_bueno": 80, "benchmark_malo": 30, "descripcion": "Porcentaje de código cubierto por tests"},
            "Lead time": {"unidad": "días", "benchmark_bueno": 3, "benchmark_malo": 21, "descripcion": "Tiempo desde que se pide una feature hasta que está en producción"},
            "Tickets IT resueltos/semana": {"unidad": "tickets", "benchmark_bueno": 50, "benchmark_malo": 15, "descripcion": "Productividad del equipo IT"},
        },
        "automatizaciones": [
            "Alerta automática de caída de sistema o servicio",
            "Backup automático diario con verificación",
            "Creación automática de ticket al detectar error en log",
            "Notificación de despliegue completado o fallido",
            "Informe semanal de estado de sistemas",
            "Aprovisionamiento automático de accesos para nuevos empleados",
        ],
        "puntos_dolor": [
            "Tiempo excesivo en tareas manuales y repetitivas de operaciones",
            "Falta de visibilidad del estado de sistemas en tiempo real",
            "Procesos de onboarding IT lentos",
        ],
        "roi_horas_mes": 38,
    },
    "legal": {
        "aliases": ["legal", "jurídico", "juridico", "compliance", "contratos", "asesoría jurídica", "asesoria juridica"],
        "procesos_tipicos": [
            "Gestión de contratos", "Due diligence", "Compliance normativo",
            "Gestión de reclamaciones legales", "Registro de propiedad intelectual",
            "Revisión de documentos", "Gestión de poderes notariales",
        ],
        "kpis": {
            "Tiempo de revisión de contratos": {"unidad": "días", "benchmark_bueno": 3, "benchmark_malo": 15, "descripcion": "Días para revisar y aprobar un contrato estándar"},
            "Contratos vencidos sin renovar": {"unidad": "unidades", "benchmark_bueno": 0, "benchmark_malo": 5, "descripcion": "Contratos que han expirado sin renovación"},
            "Coste por contrato": {"unidad": "€", "benchmark_bueno": 150, "benchmark_malo": 600, "descripcion": "Coste interno de gestionar un contrato"},
            "Tasa de incumplimiento normativo": {"unidad": "%", "benchmark_bueno": 0, "benchmark_malo": 2, "descripcion": "Procesos fuera de cumplimiento regulatorio"},
            "Litigios activos": {"unidad": "casos", "benchmark_bueno": 0, "benchmark_malo": 5, "descripcion": "Número de procedimientos judiciales activos"},
        },
        "automatizaciones": [
            "Alerta de vencimiento de contratos con 60 días de antelación",
            "Generación automática de contratos estándar desde plantilla",
            "Workflow de aprobación de contratos por importe",
            "Recordatorio de obligaciones de compliance periódicas",
            "Registro automático en base de datos de contratos",
        ],
        "puntos_dolor": [
            "Contratos que vencen sin que nadie los renueve",
            "Revisiones manuales lentas que bloquean operaciones",
            "Falta de trazabilidad en el estado de contratos",
        ],
        "roi_horas_mes": 20,
    },
    "producción": {
        "aliases": ["producción", "produccion", "manufactura", "manufacturing", "planta", "fabricación", "fabricacion", "operaciones"],
        "procesos_tipicos": [
            "Planificación de producción", "Control de calidad", "Mantenimiento preventivo",
            "Gestión de materias primas", "Control de línea", "Gestión de incidencias de planta",
            "Informes de producción", "Optimización de turnos",
        ],
        "kpis": {
            "OEE (eficiencia global)": {"unidad": "%", "benchmark_bueno": 85, "benchmark_malo": 60, "descripcion": "Overall Equipment Effectiveness — disponibilidad × rendimiento × calidad"},
            "Tasa de defectos": {"unidad": "%", "benchmark_bueno": 0.5, "benchmark_malo": 3, "descripcion": "Unidades defectuosas sobre total producido"},
            "Tiempo de cambio de formato": {"unidad": "minutos", "benchmark_bueno": 15, "benchmark_malo": 90, "descripcion": "Tiempo de changeover entre productos"},
            "MTBF equipos": {"unidad": "horas", "benchmark_bueno": 720, "benchmark_malo": 120, "descripcion": "Horas de funcionamiento entre averías"},
            "Rendimiento de línea": {"unidad": "%", "benchmark_bueno": 95, "benchmark_malo": 75, "descripcion": "Producción real vs capacidad teórica"},
            "Coste de no calidad": {"unidad": "€/mes", "benchmark_bueno": None, "benchmark_malo": None, "descripcion": "Coste total de defectos, retrabajos y rechazos"},
        },
        "automatizaciones": [
            "Alerta automática de avería o parada de máquina",
            "Informe de producción diaria automático",
            "Notificación de lote con tasa de defectos elevada",
            "Orden automática de mantenimiento preventivo",
            "Alerta de stock de materia prima por debajo de mínimo",
        ],
        "puntos_dolor": [
            "Paradas no planificadas que generan pérdidas",
            "Reporting manual de producción lento e impreciso",
            "Detección tardía de problemas de calidad",
        ],
        "roi_horas_mes": 45,
    },
    "educación": {
        "aliases": ["educación", "educacion", "formación", "formacion", "enseñanza", "enseñanza", "academia", "universidad", "colegio", "escuela"],
        "procesos_tipicos": [
            "Matrícula y admisiones", "Gestión de horarios", "Control de asistencia",
            "Evaluación y calificaciones", "Comunicación con familias", "Gestión docente",
        ],
        "kpis": {
            "Tasa de retención de alumnos": {"unidad": "%", "benchmark_bueno": 90, "benchmark_malo": 70, "descripcion": "Alumnos que completan el curso"},
            "NPS de alumnos": {"unidad": "puntos", "benchmark_bueno": 45, "benchmark_malo": 10, "descripcion": "Satisfacción de los estudiantes"},
            "Tiempo de matrícula": {"unidad": "minutos", "benchmark_bueno": 10, "benchmark_malo": 60, "descripcion": "Tiempo para completar el proceso de matrícula"},
            "Tasa de aprobados": {"unidad": "%", "benchmark_bueno": 85, "benchmark_malo": 65, "descripcion": "Porcentaje de alumnos que superan la evaluación"},
        },
        "automatizaciones": [
            "Envío automático de comunicados a familias",
            "Recordatorio de fechas de entrega a alumnos",
            "Generación automática de certificados",
            "Alerta de absentismo elevado",
        ],
        "puntos_dolor": ["Comunicación manual con familias", "Procesos de matrícula lentos"],
        "roi_horas_mes": 15,
    },
    "salud": {
        "aliases": ["salud", "sanidad", "healthcare", "médico", "medico", "hospital", "clínica", "clinica", "farmacia"],
        "procesos_tipicos": [
            "Gestión de citas", "Historia clínica digital", "Facturación a seguros",
            "Gestión de stock de medicamentos", "Informes médicos", "Coordinación entre servicios",
        ],
        "kpis": {
            "Tiempo de espera": {"unidad": "días", "benchmark_bueno": 3, "benchmark_malo": 15, "descripcion": "Días de espera para consulta"},
            "Tasa de no-show": {"unidad": "%", "benchmark_bueno": 5, "benchmark_malo": 20, "descripcion": "Citas que no se presentan sin cancelar"},
            "Ocupación de agendas": {"unidad": "%", "benchmark_bueno": 90, "benchmark_malo": 70, "descripcion": "Porcentaje de huecos en agenda ocupados"},
            "Tiempo de informe médico": {"unidad": "horas", "benchmark_bueno": 2, "benchmark_malo": 24, "descripcion": "Tiempo hasta emitir informe tras consulta"},
        },
        "automatizaciones": [
            "Recordatorio de cita por SMS/email al paciente",
            "Alerta de stock de medicamento por debajo de mínimo",
            "Generación automática de informes estándar",
            "Confirmación y gestión de citas online",
        ],
        "puntos_dolor": ["Alto índice de no-show", "Gestión manual de citas", "Burocracia administrativa"],
        "roi_horas_mes": 32,
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# INTENCIONES — patrones NLP
# ──────────────────────────────────────────────────────────────────────────────

INTENT_PATTERNS: list[dict] = [
    # ── Saludos / Social ──────────────────────────────────────────────────────
    {
        "intent": "saludo",
        "patrones": [r"\bhola\b", r"\bbuen[ao]s?\s*(días|dias|tardes|noches)\b", r"\bqué\s+tal\b",
                     r"\bcómo\s+(estás|estas|va)\b", r"\bey\b", r"\bhi\b", r"\bhello\b"],
        "peso": 1.0,
    },
    {
        "intent": "despedida",
        "patrones": [r"\badiós\b", r"\badios\b", r"\bhasta\s*(luego|pronto|mañana)\b",
                     r"\bchao\b", r"\bbye\b", r"\bnos\s+vemos\b", r"\bbuenas\s+noches\b"],
        "peso": 1.0,
    },
    {
        "intent": "agradecimiento",
        "patrones": [r"\bgraci[ao]s\b", r"\bgenial\b", r"\bperfecto\b", r"\bexcelente\b",
                     r"\bmuy\s+bien\b", r"\bestupendo\b", r"\bgran\b", r"\bbuen\s+trabajo\b",
                     r"\bagrad\w+\b"],
        "peso": 0.9,
    },
    {
        "intent": "ayuda",
        "patrones": [r"\bayuda\b", r"\bqué\s+puedes\b", r"\bqué\s+haces\b", r"\bpara\s+qué\s+sirves\b",
                     r"\bcómo\s+funciona\b", r"\bqué\s+sé\s+hacer\b", r"\bcapacidades\b",
                     r"\bqué\s+puedo\s+(pedirte|hacer)\b", r"\bmanual\b", r"\bguía\b"],
        "peso": 0.9,
    },
    # ── Procesos ──────────────────────────────────────────────────────────────
    {
        "intent": "crear_proceso",
        "patrones": [r"\bcrear?\b.*\bproceso\b", r"\bnuevo\s+proceso\b", r"\bañad[ie]r?\b.*\bproceso\b",
                     r"\bregistrar?\b.*\bproceso\b", r"\bagr[ae]gar?\b.*\bproceso\b",
                     r"\bproceso\b.*\bcrear?\b", r"\bdame\s+un\s+proceso\b"],
        "peso": 1.0,
        "entidades": ["nombre_proceso", "categoria", "responsable", "sector"],
    },
    {
        "intent": "listar_procesos",
        "patrones": [r"\bver?\b.*\bprocesos?\b", r"\blistar?\b.*\bprocesos?\b",
                     r"\bmostr[ae]r?\b.*\bprocesos?\b", r"\bqu[eé]\s+procesos?\b",
                     r"\bcuánt[ao]s\s+procesos?\b", r"\bmis\s+procesos?\b", r"\bteng[oa]\s+procesos?\b"],
        "peso": 1.0,
    },
    {
        "intent": "analizar_proceso",
        "patrones": [r"\banali[sz][ae]r?\b.*\bproceso\b", r"\banalisis\b.*\bproceso\b",
                     r"\bcómo\s+(está|esta)\b.*\bproceso\b", r"\brevisa[r]?\b.*\bproceso\b",
                     r"\bdiagnóstico\b.*\bproceso\b", r"\bproceso\b.*\banali[sz][ae]r?\b",
                     r"\bestado\s+de\b.*\bproceso\b", r"\bpuntuac[ió]n\b.*\bproceso\b"],
        "peso": 1.0,
        "entidades": ["nombre_proceso"],
    },
    {
        "intent": "editar_proceso",
        "patrones": [r"\beditar?\b.*\bproceso\b", r"\bmodificar?\b.*\bproceso\b",
                     r"\bactualizar?\b.*\bproceso\b", r"\bcambiar?\b.*\bproceso\b",
                     r"\bprocess\b.*\bupdate\b"],
        "peso": 1.0,
        "entidades": ["nombre_proceso"],
    },
    {
        "intent": "eliminar_proceso",
        "patrones": [r"\beliminar?\b.*\bproceso\b", r"\bborrar?\b.*\bproceso\b",
                     r"\bsuprimir?\b.*\bproceso\b", r"\bquitar?\b.*\bproceso\b"],
        "peso": 1.0,
        "entidades": ["nombre_proceso"],
    },
    # ── KPIs ──────────────────────────────────────────────────────────────────
    {
        "intent": "crear_kpi",
        "patrones": [r"\bcrear?\b.*\bkpi\b", r"\bnuevo\s+kpi\b", r"\bañad[ie]r?\b.*\bkpi\b",
                     r"\bregistrar?\b.*\bkpi\b", r"\bkpi\b.*\bcrear?\b"],
        "peso": 1.0,
        "entidades": ["nombre_kpi", "valor", "unidad"],
    },
    {
        "intent": "listar_kpis",
        "patrones": [r"\bver?\b.*\bkpis?\b", r"\blistar?\b.*\bkpis?\b", r"\bmostr[ae]r?\b.*\bkpis?\b",
                     r"\bqu[eé]\s+kpis?\s+tengo\b", r"\bcuánt[ao]s\s+kpis?\b", r"\bmis\s+kpis?\b"],
        "peso": 1.0,
    },
    {
        "intent": "recomendar_kpis",
        "patrones": [r"\bqu[eé]\s+kpis?\s+(debo|deber[ií]a|necesito|recomiend[ae]s?)\b",
                     r"\bkpis?\s+(?:para|en|de|del?)\b", r"\bkpis?\s+recomendad[ao]s?\b",
                     r"\bqu[eé]\s+kpis?\s+(?:debo|deber[ií]a|medir|usar)\b",
                     r"\bqu[eé]\s+(?:indicadores?|m[eé]tricas?)\s+(?:debo|deber[ií]a|necesito|recomend[ae]s?)\b",
                     r"\bqu[eé]\s+medir\b", r"\bc[oó]mo\s+medir\b", r"\bindic[ae]dores?\b.*\brecomend[ae]\b",
                     r"\brecomie?nd[ae]\w*\b.*\bindicadores?\b", r"\bindicadores?\b.*\brecomie?nd[ae]\b",
                     r"\bkpis?\s+(de|para|en)\s+\w+", r"\bmétricas?\b.*\bsector\b"],
        "peso": 1.0,
        "entidades": ["sector"],
    },
    # ── Automatizaciones ──────────────────────────────────────────────────────
    {
        "intent": "crear_automatizacion",
        "patrones": [r"\bcrear?\b.*\bauto(?:mati[sz]ac[ió]n)?\b", r"\bnueva\s+auto\b",
                     r"\bauto(?:mati[sz]ar?)\b", r"\bañad[ie]r?\b.*\bauto\b",
                     r"\bautomati[sz]ar?\b.*\bproceso\b"],
        "peso": 1.0,
    },
    {
        "intent": "listar_automatizaciones",
        "patrones": [r"\bver?\b.*\bauto(?:mati[sz]aci[oó]n)?es?\b", r"\blistar?\b.*\bauto\b",
                     r"\bqu[eé]\s+auto(?:mati[sz]aci[oó]n)?es?\b", r"\bmis\s+auto\w*\b",
                     r"\bver\s+automatizaciones?\b", r"\bautomat\w*\b.*\bver\b"],
        "peso": 1.0,
    },
    {
        "intent": "ejecutar_automatizacion",
        "patrones": [r"\bejecuta[r]?\b.*\bauto\b", r"\bland[ae]\b.*\bauto\b",
                     r"\brun\b.*\bauto\b", r"\bactivar?\b.*\bauto\b",
                     r"\blan[zs][ae]r?\b.*\bauto\b", r"\bdispara[r]?\b.*\bauto\b"],
        "peso": 1.0,
        "entidades": ["nombre_automatizacion"],
    },
    {
        "intent": "recomendar_automatizaciones",
        "patrones": [r"\bqué\s+auto(?:mati[sz]ar?)\b", r"\brecomend[ae]\b.*\bauto\b",
                     r"\bqué\s+debería\s+auto\w+\b", r"\bauto(?:mati[sz]ac[ió]n)?es?\s+recomendad[ao]s?\b",
                     r"\bsuger[ie]r?\b.*\bauto\b", r"\bcómo\s+auto(?:mati[sz]ar?)\b"],
        "peso": 1.0,
        "entidades": ["sector", "nombre_proceso"],
    },
    # ── ROI / Análisis financiero ─────────────────────────────────────────────
    {
        "intent": "calcular_roi",
        "patrones": [r"\broi\b", r"\bretorno\b",
                     r"\bcuánto\s+(me\s+)?ahorr[aío]\w*\b",
                     r"\bcu[aá]nto\s+(?:me\s+)?(?:ahorra|ahorraría|costaría|cuesta|supone)\b",
                     r"\bcu[aá]nto\s+(?:se\s+)?(?:ahorra|ahorrarí)\b",
                     r"\bahorro\s+(?:de|en|al|con)\b", r"\bme\s+(?:ahorra|ahorraría)\b",
                     r"\brentabilidad\b", r"\bpayback\b",
                     r"\binversión\b.*\bretorno\b", r"\bbeneficios?\b.*\bauto\w*\b",
                     r"\bváli[td][oa]\b.*\binvertir\b", r"\bcompensa\b",
                     r"\bcuánto\s+(?:me\s+)?(?:sale|saldría|costaría)\b.*\bautomat\w*\b"],
        "peso": 1.0,
        "entidades": ["nombre_proceso", "nombre_automatizacion", "horas_mes"],
    },
    # ── Acciones reales ───────────────────────────────────────────────────────
    {
        "intent": "enviar_email",
        "patrones": [r"\benv[íi]a[r]?\b.*\bemail\b", r"\benv[íi]a[r]?\b.*\bcorreo\b",
                     r"\benviar?\b.*\bemail\b", r"\bmandar?\b.*\bemail\b",
                     r"\benviar?\b.*\bcorreo\b", r"\bmandar?\b.*\bcorreo\b",
                     r"\bemail\b.*\benviar?\b", r"\bescribir?\b.*\bmail\b",
                     r"\bresponder?\b.*\bemail\b",
                     r"\breply\b.*\bmail\b"],
        "peso": 1.0,
        "entidades": ["email_destinatario", "asunto", "contenido"],
    },
    {
        "intent": "crear_evento_calendar",
        "patrones": [r"\bagend[ae]r?\b", r"\bcrear?\b.*\breunión\b", r"\bcrear?\b.*\bevento\b",
                     r"\breservar?\b.*\bcita\b", r"\bcalendario\b", r"\bprogramar?\b.*\breunión\b",
                     r"\bañadir?\b.*\bcalendario\b", r"\bcal[ae]ndar\b"],
        "peso": 1.0,
        "entidades": ["fecha", "hora", "titulo_evento", "participantes"],
    },
    {
        "intent": "enviar_telegram",
        "patrones": [r"\btelegram\b.*\benviar?\b", r"\benviar?\b.*\btelegram\b",
                     r"\bmandar?\b.*\btelegram\b", r"\bmensaje\b.*\btelegram\b",
                     r"\bnotificar?\b.*\btelegram\b"],
        "peso": 1.0,
        "entidades": ["contenido"],
    },
    # ── Estado / Dashboard ────────────────────────────────────────────────────
    {
        "intent": "estado_sistema",
        "patrones": [r"\bestado\s+del?\s+sistema\b", r"\bres[úu]men\b", r"\bcómo\s+va\b",
                     r"\bestado\s+general\b", r"\bvisi[oó]n\s+general\b", r"\bpanorama\b",
                     r"\bqu[eé]\s+tengo\b", r"\bdashboard\b", r"\bmis\s+datos\b",
                     r"\bcómo\s+estoy\b", r"\bsistema\b.*\boperativ[ao]\b"],
        "peso": 1.0,
    },
    # ── Confirmaciones ────────────────────────────────────────────────────────
    {
        "intent": "confirmar",
        "patrones": [r"^s[íi]$", r"^s[íi]\s*[,!.]", r"^sí\b", r"\bconfirm[ao]\b",
                     r"\badelante\b", r"\bprocede\b", r"\bde\s+acuerdo\b", r"\bok\b",
                     r"\bperfecto\b", r"\bvale\b", r"\bsí,?\s+por\s+favor\b", r"\baprov[ae]cha\b"],
        "peso": 1.0,
    },
    {
        "intent": "cancelar",
        "patrones": [r"^no[,.]?$", r"^no,\s+", r"\bcancela[r]?\b", r"\bolvida\s+(?:eso|esto|lo)\b",
                     r"\bno\s+quiero\b", r"\bno\s+hace\s+falta\b", r"\bno\s+(?:gracias|por\s+favor)\b"],
        "peso": 1.0,
    },
    # ── Sector / Empresa ─────────────────────────────────────────────────────
    {
        "intent": "info_empresa",
        "patrones": [r"\bmi\s+empresa\b", r"\bnuestra\s+empresa\b", r"\binfo\b.*\bempresa\b",
                     r"\bdatos\b.*\bempresa\b", r"\bperfil\b.*\bempresa\b"],
        "peso": 0.9,
    },
    # ── Sector específico ────────────────────────────────────────────────────
    {
        "intent": "info_sector",
        "patrones": [r"\bsector\b", r"\bindustria\b", r"\bcómo\s+está\s+el\s+sector\b",
                     r"\bbenchmark\b", r"\bcomparativa\b.*\bsector\b",
                     r"\bmejores\s+pr[aá]cticas?\b", r"\bbuenas\s+pr[aá]cticas?\b"],
        "peso": 0.8,
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# RESPUESTAS — banco de respuestas variadas por tipo
# ──────────────────────────────────────────────────────────────────────────────

RESPUESTAS: dict[str, list[str]] = {
    "saludo": [
        "¡Hola! Soy tu asistente BPA. Puedo ayudarte a analizar procesos, gestionar KPIs, configurar automatizaciones y ejecutar acciones reales. ¿Por dónde empezamos?",
        "¡Buenas! Listo para trabajar. Tengo acceso a todos tus procesos y automatizaciones. ¿Qué necesitas hoy?",
        "¡Hola! ¿Qué quieres optimizar hoy? Puedo analizar tu empresa, recomendarte KPIs, crear automatizaciones o directamente ejecutar acciones como enviar emails o agendar reuniones.",
    ],
    "despedida": [
        "¡Hasta luego! Ha sido un placer ayudarte. Aquí estaré cuando me necesites.",
        "¡Hasta pronto! Si necesitas cualquier cosa con tus procesos o automatizaciones, ya sabes dónde encontrarme.",
        "Nos vemos. Cualquier consulta sobre tus procesos BPA, aquí estoy.",
    ],
    "agradecimiento": [
        "¡De nada! ¿Hay algo más en lo que pueda ayudarte?",
        "Para eso estoy. ¿Seguimos optimizando algo más?",
        "Es un placer. ¿Quieres que revisemos algo más de tu empresa?",
        "¡Perfecto! Si necesitas cualquier otra cosa, adelante.",
    ],
    "no_entendido": [
        "No he entendido del todo bien eso. ¿Podrías reformularlo? Por ejemplo, puedo crear procesos, analizar KPIs, configurar automatizaciones o ejecutar acciones como enviar emails.",
        "Hmm, no estoy seguro de entender qué necesitas. ¿Me lo explicas de otra forma? Trabajo con procesos, KPIs, automatizaciones y puedo realizar acciones reales.",
        "No he captado bien la petición. Puedo ayudarte con: gestión de procesos y KPIs, configuración de automatizaciones, análisis ROI, o ejecutar acciones (email, calendar, telegram). ¿Qué necesitas?",
    ],
    "ayuda": [
        """Claro, aquí van mis capacidades principales:

📊 **Gestión de procesos** — crear, editar, analizar y puntuar tus procesos empresariales
📈 **KPIs** — crear indicadores, ver benchmarks por sector, recibir recomendaciones
⚡ **Automatizaciones** — configurar, ejecutar y monitorizar automatizaciones reales
💰 **Análisis ROI** — calcular el retorno de automatizar cualquier proceso
📧 **Acciones reales** — enviar emails, agendar reuniones en Calendar, enviar mensajes Telegram
🔍 **Análisis sector** — benchmarks y recomendaciones para tu industria

Prueba con cosas como: *"analiza mi proceso de facturación"*, *"¿qué KPIs debería medir en logística?"*, *"¿cuánto me ahorra automatizar la gestión de pedidos?"* o *"manda un email a juan@empresa.com"*.""",
    ],
    "confirmacion_crear_proceso": [
        "Proceso **{nombre}** creado correctamente. Score inicial: {score}/100. ¿Quieres que analice sus puntos de mejora o que te recomiende automatizaciones para él?",
        "✅ Proceso **{nombre}** registrado. He asignado un score de {score}/100 basado en los datos iniciales. ¿Añadimos KPIs o configuramos alguna automatización?",
        "Listo, **{nombre}** está en tu catálogo de procesos. Score: {score}/100. ¿Lo analizamos en profundidad?",
    ],
    "confirmacion_crear_kpi": [
        "KPI **{nombre}** creado con valor actual {valor} {unidad}. {comparativa_benchmark}",
        "✅ Indicador **{nombre}** registrado: {valor} {unidad}. {comparativa_benchmark}",
        "Listo. **{nombre}** = {valor} {unidad}. {comparativa_benchmark}",
    ],
    "error_general": [
        "Ha ocurrido un error al procesar tu solicitud: {error}. ¿Lo intentamos de nuevo?",
        "Algo ha ido mal: {error}. ¿Puedes intentarlo de nuevo?",
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# ROI — fórmulas y parámetros
# ──────────────────────────────────────────────────────────────────────────────

ROI_CONFIG = {
    "coste_hora_media": 25.0,       # € por hora de trabajo humano (España, media)
    "coste_implementacion_base": 800,  # € coste base de implementar una automatización
    "meses_amortizacion": 12,          # horizonte de análisis estándar
    "overhead_mantenimiento": 0.1,     # 10% coste mantenimiento anual
}

def calcular_roi(horas_mes: float, coste_impl: float = None, meses: int = 12) -> dict:
    coste_impl = coste_impl or ROI_CONFIG["coste_implementacion_base"]
    ahorro_mes = horas_mes * ROI_CONFIG["coste_hora_media"]
    ahorro_anual = ahorro_mes * 12
    mantenimiento_anual = coste_impl * ROI_CONFIG["overhead_mantenimiento"]
    beneficio_neto = ahorro_anual - coste_impl - mantenimiento_anual
    roi_pct = (beneficio_neto / coste_impl) * 100 if coste_impl else 0
    payback_meses = coste_impl / ahorro_mes if ahorro_mes > 0 else 999
    return {
        "ahorro_mes": round(ahorro_mes, 0),
        "ahorro_anual": round(ahorro_anual, 0),
        "coste_implementacion": round(coste_impl, 0),
        "beneficio_neto_anual": round(beneficio_neto, 0),
        "roi_pct": round(roi_pct, 1),
        "payback_meses": round(payback_meses, 1),
        "viable": payback_meses < 18,
    }


# ──────────────────────────────────────────────────────────────────────────────
# SCORING DE PROCESOS — criterios de puntuación
# ──────────────────────────────────────────────────────────────────────────────

SCORING_CRITERIOS = {
    "tiene_responsable":       {"peso": 15, "descripcion": "Proceso asignado a un responsable"},
    "tiene_descripcion":       {"peso": 10, "descripcion": "Descripción clara del proceso"},
    "tiene_kpis":              {"peso": 25, "descripcion": "KPIs definidos para medir el proceso"},
    "tiene_automatizacion":    {"peso": 20, "descripcion": "Al menos una automatización configurada"},
    "kpis_en_target":          {"peso": 20, "descripcion": "KPIs dentro del rango objetivo"},
    "auto_activa":             {"peso": 10, "descripcion": "Automatización activa y ejecutándose"},
}

def calcular_score(proceso_data: dict) -> tuple[int, list[str]]:
    """Calcula el score de un proceso y devuelve (score, mejoras_sugeridas)."""
    score = 0
    mejoras = []

    if proceso_data.get("responsable"):
        score += SCORING_CRITERIOS["tiene_responsable"]["peso"]
    else:
        mejoras.append("Asignar un responsable al proceso")

    if proceso_data.get("descripcion") and len(proceso_data["descripcion"]) > 20:
        score += SCORING_CRITERIOS["tiene_descripcion"]["peso"]
    else:
        mejoras.append("Añadir una descripción detallada")

    if proceso_data.get("kpis_count", 0) > 0:
        score += SCORING_CRITERIOS["tiene_kpis"]["peso"]
    else:
        mejoras.append("Definir KPIs para medir el rendimiento")

    if proceso_data.get("autos_count", 0) > 0:
        score += SCORING_CRITERIOS["tiene_automatizacion"]["peso"]
        score += SCORING_CRITERIOS["auto_activa"]["peso"]
    else:
        mejoras.append("Configurar al menos una automatización")

    if proceso_data.get("kpis_en_target"):
        score += SCORING_CRITERIOS["kpis_en_target"]["peso"]
    elif proceso_data.get("kpis_count", 0) > 0:
        mejoras.append("Mejorar los KPIs para alcanzar los valores objetivo del sector")

    return min(score, 100), mejoras


# ──────────────────────────────────────────────────────────────────────────────
# ENTIDADES — patrones de extracción
# ──────────────────────────────────────────────────────────────────────────────

import re

ENTITY_PATTERNS = {
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "hora": re.compile(r'\b([01]?\d|2[0-3])[:h]([0-5]\d)?\b|\b\d{1,2}\s*(de la\s*)?(mañana|tarde|noche)\b', re.I),
    "fecha_relativa": re.compile(r'\b(hoy|mañana|pasado\s+mañana|lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo|esta\s+semana|próxima\s+semana|próximo\s+\w+)\b', re.I),
    "fecha_absoluta": re.compile(r'\b(\d{1,2})[/\-\.](\d{1,2})(?:[/\-\.](\d{2,4}))?\b'),
    "porcentaje": re.compile(r'\b(\d+(?:[.,]\d+)?)\s*%'),
    "numero": re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(horas?|días?|dias?|€|euros?|minutos?|meses?)?\b', re.I),
    "sector": None,  # se calcula dinámicamente contra SECTORES
}

def _normalizar(s: str) -> str:
    """Elimina acentos para comparación flexible."""
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def detectar_sector(texto: str) -> str | None:
    import re
    texto_lower = texto.lower()
    texto_norm = _normalizar(texto_lower)
    palabras_norm = set(re.split(r'\W+', texto_norm))
    for sector, data in SECTORES.items():
        for alias in data["aliases"]:
            alias_norm = _normalizar(alias.lower())
            # Aliases cortos (<= 3 chars) requieren coincidencia de palabra completa
            if len(alias_norm) <= 3:
                if alias_norm in palabras_norm:
                    return sector
            else:
                if alias_norm in texto_norm:
                    return sector
    return None

def detectar_nombre_proceso(texto: str, procesos_disponibles: list[str]) -> str | None:
    """Intenta encontrar un proceso conocido en el texto."""
    texto_lower = texto.lower()
    for nombre in procesos_disponibles:
        if nombre.lower() in texto_lower:
            return nombre
    # Si no encuentra exacto, busca coincidencia parcial (>60% de palabras)
    palabras_texto = set(texto_lower.split())
    mejor = None
    mejor_score = 0
    for nombre in procesos_disponibles:
        palabras_nombre = set(nombre.lower().split())
        coincidencias = len(palabras_texto & palabras_nombre)
        if coincidencias > 0 and len(palabras_nombre) > 0:
            s = coincidencias / len(palabras_nombre)
            if s > mejor_score and s >= 0.5:
                mejor_score = s
                mejor = nombre
    return mejor
