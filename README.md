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
| `SMTP_EMAIL`, `SMTP_PASSWORD` | Gmail for password reset + email verification |
| `RESEND_API_KEY` | Optional Resend API for emails |
| `RESEND_FROM` | Sender e.g. `Plant Doctor <onboarding@resend.dev>` |
| `APP_BASE_URL` | Streamlit app URL for email links |
| `REQUIRE_EMAIL_VERIFY` | `true` (default) or `false` for dev |
| `STRIPE_SECRET_KEY` | Stripe secret (Premium payments) |
| `STRIPE_PRICE_ID` | Stripe Price ID for Premium product |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `PREMIUM_DAYS` | Premium duration after payment (default: 30) |

## Email verify — simple guide (Urdu)

**Agar Railway par kuch set NA karo:** register ke baad **seedha login** ho jata hai (auto-verify).

**Agar email verify chahiye:**

1. [Google App Password](https://myaccount.google.com/apppasswords) banao (2-step ON hona chahiye)
2. Railway → project → **Variables**:
   - `SMTP_EMAIL` = `tumhara@gmail.com`
   - `SMTP_PASSWORD` = 16-character app password
3. User register kare → email mein link → click → login

**Resend use karna ho:** `RESEND_API_KEY` + optional `RESEND_FROM`

## Premium (Stripe)

1. [stripe.com](https://stripe.com) account → Product + Price banao
2. Railway Variables: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`
3. Stripe Dashboard → Webhooks → endpoint:  
   `https://plant-doctor-app-production.up.railway.app/api/payments/webhook`  
   Event: `checkout.session.completed`
4. App → sidebar **Premium** → Upgrade button

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

## Run tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -q
```

See `current_state_analysis.md` for full feature status.
