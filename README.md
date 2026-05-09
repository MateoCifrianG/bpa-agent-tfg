# BPA-Agent

Agente inteligente de automatización de procesos empresariales (BPA).  
Proyecto de Fin de Grado — Mateo Cifrián, 2025-2026.

## Estructura del proyecto

```
TFG/
├── backend/                  # API FastAPI (Python)
│   ├── app/
│   │   ├── agents/           # Motor razonador IA (v4, v5, v6)
│   │   ├── auth/             # JWT + refresh tokens
│   │   ├── middleware/       # Rate limiting, seguridad
│   │   ├── models/           # Modelos SQLAlchemy
│   │   ├── routers/          # Endpoints REST
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/
│   │       ├── connectors/   # Email, Telegram, Webhook, Gmail, Calendar
│   │       └── integrations/ # Google OAuth2, n8n, Notion
│   ├── scripts/              # Utilidades (seed, audit, check_env)
│   ├── tests/                # Tests (pytest)
│   ├── .env                  # Variables de entorno (NO subir a git)
│   ├── .env.example          # Plantilla de configuración
│   └── requirements.txt
├── frontend/                 # Interfaz HTML/JS/CSS
│   ├── assets/
│   │   ├── css/
│   │   ├── img/
│   │   └── js/               # api.js, dashboard.js
│   ├── admin.html
│   ├── dashboard.html
│   ├── login.html
│   ├── register.html
│   └── settings.html
├── residual/                 # Archivos históricos / prototipos anteriores
├── docker-compose.dev.yml
└── README.md
```

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.ai) con `llama3.1:8b` (opcional, para motor v5)

## Arrancar en desarrollo

```bash
# 1. Backend
cd backend
cp .env.example .env        # editar con tus valores
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002

# 2. Frontend
cd frontend
python -m http.server 3333
```

Abre `http://localhost:3333/login.html`  
Admin: `admin@bpa.com` / `Admin1234!`

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI + SQLAlchemy async + SQLite/PostgreSQL |
| Auth | JWT (access 8h + refresh 7d) |
| Motor IA | Pipeline NLP propio (v6) + Ollama fallback |
| Frontend | HTML + CSS + JS vanilla |
| Conectores | SMTP, Telegram, Webhook, Gmail API, Google Calendar API |
