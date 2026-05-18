# Plant Doctor AI — Pakistani Kisanon Ka AI Doctor

Streamlit frontend + FastAPI backend for leaf disease detection (potato, tomato, pepper, corn) with Roman Urdu AI advice.

## Live URLs

| Service | URL |
|---------|-----|
| App (Streamlit Cloud) | https://plantdoctorapp.streamlit.app |
| API (Railway) | https://plant-doctor-app-production.up.railway.app |

## Quick start (local)

### 1. Frontend (Streamlit)

```bash
pip install -r requirements.txt
# Create .streamlit/secrets.toml with: GEMINI_API_KEY = "your-key"
streamlit run app.py
```

### 2. Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
# Optional: set MYSQL_URL or DATABASE_URL for MySQL; else uses local SQL Server
uvicorn main:app --reload --port 8000
```

In `app.py`, uncomment `API_URL = "http://localhost:8000/api"` for local API testing.

## Environment variables (Railway / production)

| Variable | Purpose |
|----------|---------|
| `MYSQL_URL` or `DATABASE_URL` | MySQL connection string |
| `JWT_SECRET` or `SECRET_KEY` | JWT signing key (required in production) |
| `JWT_EXPIRE_DAYS` | Token lifetime (default: 7) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `SMTP_EMAIL`, `SMTP_PASSWORD` | Gmail for password reset emails |

## Project structure

```
app.py                 # Streamlit UI + ML inference
backend/main.py        # FastAPI REST API
backend/pwa/           # Installable PWA shell
*.pkl                  # Trained XGBoost models (Git LFS)
database.sql           # SQL Server schema reference
current_state_analysis.md  # Feature checklist (updated)
```

## API highlights

- `POST /api/auth/login` — JWT (7-day expiry)
- `POST /api/scans` — saves scan + image in DB + `ai_advice`
- `GET /api/scans/{id}/image` — retrieve scan photo
- `GET /api/diseases?crop=potato&disease=Late Blight` — knowledge base
- `GET /api/admin/stats` — admin dashboard (admin role only)

See `current_state_analysis.md` for full feature status.
