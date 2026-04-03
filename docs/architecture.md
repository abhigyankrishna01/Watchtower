# Watchtower Architecture

## Overview
Watchtower is an automated API monitoring platform with a FastAPI control plane and Celery workers that execute checks in parallel. Validation logic is isolated from execution logic to keep the system extensible and testable.

## Components
- **FastAPI app**: Stores monitor definitions, triggers runs, exposes metrics and results.
- **Scheduler**: Enqueues periodic checks using Celery (Celery Beat or external scheduler).
- **Celery workers**: Execute HTTP checks, validate responses, and emit metrics.
- **Validation engine**: Pluggable validators for status code, JSON schema, and latency thresholds.
- **Observability**: Prometheus metrics and Grafana dashboards.
- **Persistence**: Postgres (SQLAlchemy) with Alembic migrations.

## Production Notes
- Use a persistent datastore for monitors/results (Postgres + SQLAlchemy/SQLModel).
- Keep workers stateless and scale horizontally.
- Protect management endpoints with API keys or JWT.
- Store secrets outside of version control.
- Use Celery Beat to dispatch scheduled monitors at a fixed cadence.
