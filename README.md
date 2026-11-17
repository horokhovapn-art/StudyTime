# StudyTime

An adaptive web planner for students. Enter your fixed schedule (lectures, work, sleep) and your goals
(weekly targets and deadlines); the **Smart Fit** algorithm places study blocks into the free windows without
exceeding a daily workload limit. When a block is missed, **Replan** rebuilds the rest of the week in one click.

Team: Sofiia Volvach, Sofiia Horokhova. Course: Architecture and Design, UCU, Fall 2026.

**Demo:** https://63.176.50.123.nip.io ·  Sign up with any email and a password of 6+ characters.

## Features
- Sign-up / sign-in (JWT, PBKDF2-hashed passwords); every user sees only their own data
- Weekly calendar with fixed events, tasks (weekly goals / deadlines), categories and a daily-load limit
- Smart Fit planning, one-click Replan, mark done / missed, drag blocks to move them, drag a task into the calendar
- In-app feedback form (used for the user-validation report)

## Repository layout
| Path | What |
|---|---|
| `backend/` | FastAPI + SQLite: auth, API, planning algorithm (`app.py`); `stats.py` prints usage numbers |
| `frontend/` | Single-page UI (`index.html`), served by the backend |
| `infra/` | `Dockerfile`, `docker-compose.yml` + `Caddyfile` (automatic HTTPS), `.env.example` |
| `docs/` | Report template and survey questions |

## Run locally
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend && JWT_SECRET=anything python -m uvicorn app:app --reload   # http://localhost:8000
```

## Deploy
Environment variables: `JWT_SECRET` (**required**, long random string), `DB_PATH` (default `studytime.db`;
the Docker image uses `/data/studytime.db`), `PORT` (set by most platforms).

**A. Any Docker host with a persistent volume (Render with a disk, Railway, Fly.io):**
build from `infra/Dockerfile` (context = repository root), mount a volume at `/data`, set `JWT_SECRET`.
HTTPS is provided by the platform. Without a volume the SQLite file is wiped on every deploy and accounts disappear.

**B. Own VPS + domain (HTTPS via Caddy):**
```bash
cd infra && cp .env.example .env     # set DOMAIN and JWT_SECRET
docker compose up -d --build
```

## Usage numbers and feedback
`cd backend && python stats.py` prints registered users, how many created a plan, and all feedback entries.

## Limitations (prototype)
Planning covers the current calendar week only; study window is fixed at 08:00-22:00; fixed events repeat weekly;
no e-mail verification or password reset; SQLite is not meant for high load (PostgreSQL would be the next step).
