# Arquitectura BPA-Agent

## Backend (FastAPI)

```
app/
├── main.py              # Arranque, middlewares, lifespan
├── config.py            # Settings (pydantic-settings, .env)
├── database.py          # Engine async SQLite/PostgreSQL
│
├── agents/              # Motor razonador IA
│   ├── motor_v4.py      # Pipeline NLP puro (siempre disponible)
│   ├── motor_v5.py      # Ollama LLM (fallback v4)
│   ├── motor_v6.py      # Motor propio conversacional (en desarrollo)
│   ├── prompts/         # Templates de prompts para LLM
│   └── safety.py        # Validación de inputs
│
├── auth/
│   └── jwt.py           # Hash, verify, create/decode tokens
│
├── middleware/
│   └── rate_limit.py    # 60 req/min por IP
│
├── models/              # SQLAlchemy ORM
│   ├── user.py
│   ├── empresa.py
│   ├── proceso.py
│   ├── kpi.py
│   ├── automatizacion.py
│   ├── conversacion.py
│   ├── credencial.py    # Credenciales cifradas (Fernet AES-256)
│   └── ejecucion_log.py
│
├── routers/             # Endpoints REST (/api/*)
│   ├── auth.py          # /api/auth/login, register, refresh, me
│   ├── users.py         # /api/users/me
│   ├── empresas.py      # /api/empresa/mia
│   ├── procesos.py      # /api/procesos
│   ├── kpis.py          # /api/kpis
│   ├── automatizaciones.py
│   ├── agente.py        # /api/agente/chat  ← motor IA
│   ├── ejecutar.py      # /api/ejecutar/{auto_id}
│   ├── integraciones.py # /api/integraciones/google/*
│   ├── credenciales.py
│   └── admin.py         # /api/admin/* (solo role=admin)
│
└── services/
    ├── connectors/      # Conectores de acción
    │   ├── email_connector.py
    │   ├── telegram_connector.py
    │   ├── webhook_connector.py
    │   ├── gmail_connector.py    (en desarrollo)
    │   └── calendar_connector.py (en desarrollo)
    ├── integrations/    # OAuth2 y servicios externos
    │   ├── google_oauth.py
    │   ├── gmail_service.py
    │   ├── gcalendar_service.py
    │   ├── n8n_service.py
    │   └── notion_service.py
    ├── automation_executor.py  # Ejecuta automatizaciones reales
    ├── scheduler.py            # APScheduler (cron jobs)
    ├── credenciales_service.py # Cifrado/descifrado credenciales
    └── mcp_service.py          # Model Context Protocol
```

## Flujo del Motor IA

```
[Mensaje] → Motor v6 (NLP propio)
               ↓ intención detectada con alta confianza
           Acción directa (CRUD, análisis, ejecución)
               ↓ intención ambigua / redacción compleja
           Motor v5 (Ollama llama3.1:8b — local, gratuito)
               ↓ Ollama no disponible
           Motor v4 (NLP regex — siempre activo)
```

## Seguridad

- JWT HS256 (access 8h + refresh 7d)
- Rate limiting: 60 req/min por IP
- Credenciales cifradas con Fernet AES-256
- CORS configurado por entorno (DEBUG vs producción)
- Headers: X-Frame, XSS, Content-Type, Referrer
- Body limit: 1 MB
