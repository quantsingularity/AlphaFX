# AlphaFX Scripts

All operational scripts for development, deployment, database management,
AI model training, and platform maintenance.

Make scripts executable before first use:

```bash
chmod +x scripts/**/*.sh
# or recursively:
find scripts -name "*.sh" -exec chmod +x {} \;
```

---

## Directory Layout

```
scripts/
  dev/
    setup.sh                Bootstrap local development environment
    start_all.sh            Start all services for local development
    stop_all.sh             Stop all local services and free ports
    run_tests.sh            Run backend and AI test suites with coverage
    lint.sh                 Lint and format-check Python and TypeScript
  db/
    migrate.sh              Run Django database migrations safely
    backup.sh               Backup PostgreSQL database to a timestamped file
    restore.sh              Restore a database from a backup file
    seed.sh                 Populate development database with sample data
  deploy/
    build.sh                Build all Docker images
    deploy.sh               Full production deployment with pre-flight checks
    rollback.sh             Roll back to a previous deployment tag
  ai/
    train_models.sh         Train LSTM, HMM, GARCH, and anomaly models
    evaluate_models.sh      Evaluate trained model accuracy metrics
  maintenance/
    health_check.sh         Platform-wide service health check
    clean.sh                Remove build artifacts, logs, and Docker resources
    generate_secret_key.sh  Generate a secure Django SECRET_KEY
    check_updates.sh        Report outdated Python and npm dependencies
```

---

## Development Scripts

### setup.sh

Bootstraps the full development environment from a clean clone.
Runs once after cloning.

```bash
./scripts/dev/setup.sh
```

| Action                              | Notes                                      |
| ----------------------------------- | ------------------------------------------ |
| Checks Python 3.12+ and Node.js 20+ | Exits with error if missing                |
| Copies .env.example to .env         | Configures SQLite for local use            |
| Creates backend .venv               | Installs all requirements.txt dependencies |
| Runs Django migrate                 | Applies all database migrations            |
| Prompts for superuser creation      | Optional Django admin account              |
| Creates AI services .venv           | Installs core ML dependencies              |
| Runs npm install                    | Installs frontend dependencies             |

### start_all.sh

Starts Django (8000), AI service (8001), and frontend dev server (5173).
Uses tmux panes if tmux is installed, otherwise background processes.

```bash
./scripts/dev/start_all.sh
./scripts/dev/start_all.sh --no-ai        # skip AI service
./scripts/dev/start_all.sh --no-frontend  # skip frontend
```

### stop_all.sh

Kills all services started by start_all.sh. Clears ports 8000, 8001, 5173.

```bash
./scripts/dev/stop_all.sh
```

### run_tests.sh

Runs the full test suite with HTML coverage reports.

```bash
./scripts/dev/run_tests.sh                 # all suites
./scripts/dev/run_tests.sh --backend-only  # Django tests only
./scripts/dev/run_tests.sh --ai-only       # AI service tests only
./scripts/dev/run_tests.sh --no-coverage   # skip coverage report
```

| Suite       | Tests | Output location       |
| ----------- | ----- | --------------------- |
| Backend     | 88    | coverage/backend/     |
| AI services | 20    | coverage/ai_services/ |
| Total       | 108   |                       |

### lint.sh

Runs ruff (linter), black (formatter), and tsc (TypeScript type check).

```bash
./scripts/dev/lint.sh         # check only
./scripts/dev/lint.sh --fix   # auto-fix Python issues
```

---

## Database Scripts

### migrate.sh

Applies Django migrations with pre/post state display.

```bash
./scripts/db/migrate.sh                  # local venv
./scripts/db/migrate.sh --docker         # via docker compose exec
./scripts/db/migrate.sh --check          # show pending, do not apply
./scripts/db/migrate.sh --app portfolio  # migrate a single app
```

### backup.sh

Creates a compressed, timestamped PostgreSQL dump in the backups/ directory.
Automatically keeps only the last 10 backups.

```bash
./scripts/db/backup.sh                       # Docker Compose mode
./scripts/db/backup.sh --local               # local pg_dump
./scripts/db/backup.sh --output /my/backups  # custom output path
```

Output filename format: `alphafx_backup_YYYYMMDD_HHMMSS.sql.gz`

### restore.sh

Restores a backup. Drops and recreates the database, then runs migrations.

```bash
./scripts/db/restore.sh --list                              # show available backups
./scripts/db/restore.sh backups/alphafx_backup_20250101.sql.gz
```

WARNING: This operation is destructive and requires typing 'yes' to confirm.

### seed.sh

Populates the database with realistic sample data for development and demos.
Creates 3 portfolios, 8 positions, and 5 price alerts.

```bash
./scripts/db/seed.sh             # append to existing data
./scripts/db/seed.sh --reset     # clear all data first
./scripts/db/seed.sh --docker    # seed via Docker Compose
```

| Portfolio             | Balance       | Positions         |
| --------------------- | ------------- | ----------------- |
| Trend Following Fund  | 500,000 USD   | 3 (EUR, GBP, JPY) |
| Carry Trade Portfolio | 250,000 USD   | 3 (TRY, NZD, JPY) |
| Macro Hedging Book    | 1,000,000 USD | 2 (EUR, CHF)      |

---

## Deployment Scripts

### build.sh

Builds Docker images for all or a specific service.

```bash
./scripts/deploy/build.sh
./scripts/deploy/build.sh --no-cache
./scripts/deploy/build.sh --service backend
./scripts/deploy/build.sh --push --registry registry.example.com/alphafx
```

### deploy.sh

Full production deployment with pre-flight checks, tests, migrations,
and rolling service restart.

```bash
./scripts/deploy/deploy.sh
./scripts/deploy/deploy.sh --skip-tests    # bypass test run
./scripts/deploy/deploy.sh --service backend  # single service
```

| Deployment Step      | Description                                  |
| -------------------- | -------------------------------------------- |
| Pre-flight checks    | Validates .env, SECRET_KEY, Docker presence  |
| Test suite           | Runs 108 tests (skippable with --skip-tests) |
| Build images         | Docker Compose build                         |
| Database migrations  | python manage.py migrate                     |
| Collect static files | python manage.py collectstatic               |
| Rolling restart      | backend, ai_services, frontend, nginx        |
| Health check         | Verifies /health endpoints after restart     |

### rollback.sh

Rolls back to a previous git tag or the previous Docker image.

```bash
./scripts/deploy/rollback.sh --list          # list available tags
./scripts/deploy/rollback.sh --tag v1.2.3    # rollback to specific tag
```

---

## AI Scripts

### train_models.sh

Trains all ML models (LSTM, HMM, GARCH, Isolation Forest) for a set of pairs.

```bash
./scripts/ai/train_models.sh                           # all major pairs
./scripts/ai/train_models.sh --pairs EURUSD GBPUSD     # specific pairs
./scripts/ai/train_models.sh --docker                  # via Docker
./scripts/ai/train_models.sh --lookback 90             # 90-bar LSTM window
```

Models are saved to `code/ai_services/saved_models/{PAIR}/`.
A `training_manifest.json` summary is written after training completes.

Optional dependencies (install in AI venv if needed):

| Package  | Used by          | Install command      |
| -------- | ---------------- | -------------------- |
| hmmlearn | Regime detector  | pip install hmmlearn |
| arch     | GARCH forecaster | pip install arch     |
| torch    | LSTM forecaster  | pip install torch    |

### evaluate_models.sh

Evaluates trained model accuracy on a held-out test set.

```bash
./scripts/ai/evaluate_models.sh               # all trained pairs
./scripts/ai/evaluate_models.sh --pair EURUSD # specific pair
```

Reports per-pair accuracy, precision, recall, F1, and confusion matrix.

---

## Maintenance Scripts

### health_check.sh

Checks all services and reports status. Suitable for cron monitoring.

```bash
./scripts/maintenance/health_check.sh          # human-readable
./scripts/maintenance/health_check.sh --json   # machine-readable JSON
./scripts/maintenance/health_check.sh --slack https://hooks.slack.com/...
```

Exits with code 0 if all healthy, 1 if any check fails.
The --slack flag posts an alert to a Slack webhook when status is degraded.

### clean.sh

Removes build artifacts, logs, coverage reports, and compiled files.

```bash
./scripts/maintenance/clean.sh            # code artifacts only
./scripts/maintenance/clean.sh --docker   # also remove containers
./scripts/maintenance/clean.sh --all      # also remove Docker volumes (destructive)
```

### generate_secret_key.sh

Generates a 50-character cryptographically secure Django SECRET_KEY.

```bash
./scripts/maintenance/generate_secret_key.sh           # print only
./scripts/maintenance/generate_secret_key.sh --write   # update .env in place
```

### check_updates.sh

Reports outdated dependencies across backend, AI services, and frontend.

```bash
./scripts/maintenance/check_updates.sh
```

---

## Common Workflows

### First-time setup

```bash
./scripts/dev/setup.sh
./scripts/db/seed.sh
./scripts/dev/start_all.sh
```

### Daily development

```bash
./scripts/dev/start_all.sh
# ... develop ...
./scripts/dev/run_tests.sh
./scripts/dev/stop_all.sh
```

### Before deploying

```bash
./scripts/dev/run_tests.sh
./scripts/db/backup.sh
./scripts/deploy/deploy.sh
```

### Train and evaluate AI models

```bash
./scripts/ai/train_models.sh --pairs all
./scripts/ai/evaluate_models.sh
```

### Routine maintenance

```bash
./scripts/maintenance/health_check.sh
./scripts/db/backup.sh
./scripts/maintenance/check_updates.sh
```
