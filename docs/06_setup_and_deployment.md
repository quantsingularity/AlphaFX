# AlphaFX Setup and Deployment Guide

---

## Prerequisites

| Tool       | Minimum version | Notes                                    |
| ---------- | --------------- | ---------------------------------------- |
| Python     | 3.12            | Required for backend and AI service      |
| Node.js    | 20              | Required for frontend build              |
| Docker     | 24              | Required for containerised deploy        |
| PostgreSQL | 16              | Required for production (SQLite for dev) |
| Redis      | 7               | Required for caching and WebSocket       |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in values before starting.

| Variable             | Default                  | Description                             |
| -------------------- | ------------------------ | --------------------------------------- |
| SECRET_KEY           | (insecure dev key)       | Django secret key, change in production |
| DEBUG                | False                    | Enable Django debug mode                |
| ALLOWED_HOSTS        | localhost,127.0.0.1      | Comma-separated allowed host names      |
| CORS_ALLOWED_ORIGINS | http://localhost:3000    | Allowed CORS origins                    |
| DATABASE_URL         | sqlite:///db.sqlite3     | Database connection string              |
| DB_PASSWORD          | alphafx_secret           | PostgreSQL password (Docker Compose)    |
| REDIS_URL            | redis://localhost:6379/0 | Redis connection URL                    |
| EXCHANGERATE_API_KEY | (empty)                  | ExchangeRate-API key (optional)         |
| ALPHA_VANTAGE_KEY    | (empty)                  | Alpha Vantage API key (optional)        |
| CACHE_TTL            | 60                       | Default cache TTL in seconds            |
| RISK_FREE_RATE       | 0.05                     | Risk-free rate for analytics (5%)       |
| AI_MODEL_DIR         | ./saved_models           | Path for AI service model storage       |

---

## Local Development (No Docker)

### Backend

```bash
cd code/backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp ../../.env.example ../../.env
# Set DATABASE_URL=sqlite:///db.sqlite3 for local dev

python manage.py migrate
python manage.py createsuperuser   # Create admin user
python manage.py runserver         # Start on port 8000
```

### AI Services

```bash
cd code/ai_services
pip install -r requirements.txt

# Start the AI FastAPI service
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev                        # Vite dev server on port 5173
```

---

## Docker Compose (Full Stack)

```bash
# From project root
cp .env.example .env
# Edit .env: set SECRET_KEY and DB_PASSWORD

docker compose up --build

# Access points after startup:
# Platform:     http://localhost
# Django API:   http://localhost:8000/docs/
# AI Service:   http://localhost:8001/docs
# Admin panel:  http://localhost:8000/admin/
# WebSocket:    ws://localhost:8000/ws/rates/EURUSD/
```

### Service startup order

```
db (health check) -> redis (health check) -> backend -> ai_services -> frontend -> nginx
```

---

## Running Tests

### Backend (88 tests)

```bash
cd code/backend
python -m pytest tests/ -v
```

### AI Services (20 tests)

```bash
cd code/ai_services
python -m pytest tests/test_ai_services.py -v
```

---

## Training AI Models

```bash
cd code/ai_services

# Train all major pairs (requires hmmlearn and arch)
pip install hmmlearn arch
python -m training.train_all --pairs all --output-dir ./saved_models

# Train a single pair
python -m training.train_all --pairs EURUSD
```

Models are saved under `saved_models/{PAIR}/{model_type}/`.
The AI service loads models lazily on first request per pair.

---

## Production Checklist

| Step | Action                                                             |
| ---- | ------------------------------------------------------------------ |
| 1    | Set SECRET_KEY to a random 50+ character string                    |
| 2    | Set DEBUG=False                                                    |
| 3    | Set ALLOWED_HOSTS to your domain names                             |
| 4    | Set DATABASE_URL to a managed PostgreSQL instance                  |
| 5    | Set REDIS_URL to a managed Redis instance                          |
| 6    | Configure CORS_ALLOWED_ORIGINS to your frontend domain             |
| 7    | Run python manage.py migrate                                       |
| 8    | Run python manage.py collectstatic                                 |
| 9    | Create admin user with python manage.py createsuperuser            |
| 10   | Start backend with daphne alphafx.asgi:application                 |
| 11   | Start AI service with uvicorn ai_services.api.main:app --port 8001 |
| 12   | Configure nginx with the provided nginx.conf                       |
| 13   | Train AI models with python -m training.train_all --pairs all      |

---

## Nginx Configuration

The provided `infrastructure/nginx/nginx.conf` handles:

| Location | Behaviour                                         |
| -------- | ------------------------------------------------- |
| /static/ | Served directly from filesystem, 30-day cache     |
| /ws/     | Proxied to Daphne with WebSocket upgrade headers  |
| /api/    | Proxied to Django backend                         |
| /admin/  | Proxied to Django backend                         |
| /docs/   | Proxied to Django backend                         |
| /ai/     | Proxied to AI services (port 8001)                |
| /        | Served from React SPA build (index.html fallback) |

---

## Upgrading

```bash
# Pull latest code
git pull

# Backend migrations
cd code/backend
python manage.py migrate

# Rebuild containers
docker compose up --build --no-deps backend ai_services
```

---

## Troubleshooting

| Symptom                          | Likely cause           | Resolution                                 |
| -------------------------------- | ---------------------- | ------------------------------------------ |
| django.db.OperationalError       | Database not ready     | Wait for db healthcheck to pass            |
| redis.exceptions.ConnectionError | Redis not reachable    | Check REDIS_URL, cache degrades gracefully |
| ModuleNotFoundError: channels    | channels not installed | pip install channels==4.1.0                |
| 429 Too Many Requests            | Rate limit hit         | Authenticate to get 1000/min limit         |
| AI endpoint returns 500          | Model not yet trained  | Run training pipeline first                |
| WebSocket connection refused     | Nginx not upgraded     | Check /ws/ location block in nginx.conf    |

---

## Scripts Reference

All operational scripts live in the scripts/ directory.
See scripts/README.md for full documentation.

| Script                                     | Purpose                                       |
| ------------------------------------------ | --------------------------------------------- |
| scripts/dev/setup.sh                       | Bootstrap local environment from scratch      |
| scripts/dev/start_all.sh                   | Start all services locally                    |
| scripts/dev/stop_all.sh                    | Stop all services and free ports              |
| scripts/dev/run_tests.sh                   | Run 108 tests with HTML coverage              |
| scripts/dev/lint.sh                        | Lint Python and TypeScript                    |
| scripts/db/migrate.sh                      | Apply Django migrations                       |
| scripts/db/backup.sh                       | Backup PostgreSQL to timestamped .sql.gz      |
| scripts/db/restore.sh                      | Restore from a backup file                    |
| scripts/db/seed.sh                         | Populate dev database with sample data        |
| scripts/deploy/build.sh                    | Build Docker images                           |
| scripts/deploy/deploy.sh                   | Full production deploy with pre-flight checks |
| scripts/deploy/rollback.sh                 | Roll back to a previous release tag           |
| scripts/ai/train_models.sh                 | Train all ML models for major pairs           |
| scripts/ai/evaluate_models.sh              | Evaluate model accuracy metrics               |
| scripts/maintenance/health_check.sh        | Check all service endpoints                   |
| scripts/maintenance/clean.sh               | Remove build artifacts and cache              |
| scripts/maintenance/generate_secret_key.sh | Generate secure Django SECRET_KEY             |
| scripts/maintenance/check_updates.sh       | Report outdated dependencies                  |
