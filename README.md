# AlphaFX

Institutional-grade FX analytics and trading intelligence platform.
Django 5 backend, FastAPI AI microservice, React 18 frontend.

---

## Project Layout

```
AlphaFX/
  code/
    backend/           Django REST API + WebSocket server
    ai_services/       ML inference microservice (LSTM, HMM, GARCH, sentiment)
  frontend/            React 18 SPA
  docs/                Platform documentation (9 documents)
  scripts/             Operational scripts (dev, db, deploy, ai, maintenance)
  infrastructure/      Nginx reverse proxy configuration
  docker-compose.yml   Full-stack orchestration (6 services)
  .env.example         Environment variable reference
```

---

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

| Endpoint         | URL                                  |
| ---------------- | ------------------------------------ |
| Platform         | http://localhost                     |
| Django API docs  | http://localhost:8000/docs/          |
| AI Service docs  | http://localhost:8001/docs           |
| Admin panel      | http://localhost:8000/admin/         |
| Live tick stream | ws://localhost:8000/ws/rates/EURUSD/ |

---

## Documentation

| Document                        | Content                                       |
| ------------------------------- | --------------------------------------------- |
| docs/01_overview.md             | Feature matrix, architecture summary          |
| docs/02_architecture.md         | Service topology, DB schema, caching strategy |
| docs/03_api_reference.md        | Full endpoint reference with request/response |
| docs/04_quantitative_models.md  | GK options, CIP forwards, GARCH, indicators   |
| docs/05_ai_ml_services.md       | LSTM, HMM, GARCH, anomaly, sentiment details  |
| docs/06_setup_and_deployment.md | Local dev, Docker, production checklist       |
| docs/07_frontend_guide.md       | Pages, components, API client, conventions    |
| docs/08_testing_guide.md        | Test classes, key assertions, CI pipeline     |
| docs/09_changelog.md            | Version history and feature additions         |
| scripts/README.md               | All scripts reference with usage examples     |

---

## Test Results

```
code/backend:       88 / 88 passed
code/ai_services:   20 / 20 passed
Total:              108 / 108 passed
```

---

## License

MIT License. Copyright 2025 QuantSingularity Research Institute.
