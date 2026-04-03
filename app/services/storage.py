from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.api.schemas import CheckResult, Monitor
from app.db.models import CheckResultModel, MonitorModel
from app.db.session import SessionLocal


def _to_monitor(model: MonitorModel) -> Monitor:
    return Monitor(
        id=model.id,
        name=model.name,
        url=model.url,
        method=model.method,
        headers=model.headers,
        expected_status=model.expected_status,
        json_schema=model.json_schema,
        timeout_seconds=model.timeout_seconds,
        latency_ms_threshold=model.latency_ms_threshold,
        schedule_seconds=model.schedule_seconds,
        created_at=model.created_at,
    )


def _to_result(model: CheckResultModel) -> CheckResult:
    return CheckResult(
        run_id=model.run_id,
        monitor_id=model.monitor_id,
        status=model.status,
        latency_ms=model.latency_ms,
        status_code=model.status_code,
        error_message=model.error_message,
        response_sample=model.response_sample,
        validated_at=model.validated_at,
    )


class DatabaseStore:
    def add_monitor(self, monitor: Monitor) -> Monitor:
        data = monitor.model_dump()
        data["url"] = str(monitor.url)
        data["id"] = str(monitor.id)
        with SessionLocal() as session:
            model = MonitorModel(**data)
            session.add(model)
            session.commit()
            session.refresh(model)
            return _to_monitor(model)

    def list_monitors(self) -> list[Monitor]:
        with SessionLocal() as session:
            items = session.scalars(select(MonitorModel)).all()
            return [_to_monitor(item) for item in items]

    def get_monitor(self, monitor_id: UUID) -> Monitor | None:
        with SessionLocal() as session:
            model = session.get(MonitorModel, str(monitor_id))
            return _to_monitor(model) if model else None

    def add_result(self, result: CheckResult) -> None:
        data = result.model_dump()
        data["run_id"] = str(result.run_id)
        data["monitor_id"] = str(result.monitor_id)
        with SessionLocal() as session:
            model = CheckResultModel(**data)
            session.add(model)
            session.commit()

    def list_results(self, monitor_id: UUID | None = None) -> list[CheckResult]:
        with SessionLocal() as session:
            stmt = select(CheckResultModel)
            if monitor_id is not None:
                stmt = stmt.where(CheckResultModel.monitor_id == str(monitor_id))
            items = session.scalars(stmt).all()
            return [_to_result(item) for item in items]

    def list_scheduled_due(self, now: datetime | None = None) -> list[Monitor]:
        now = now or datetime.now(timezone.utc)
        with SessionLocal() as session:
            items = session.scalars(select(MonitorModel).where(MonitorModel.schedule_seconds.is_not(None))).all()
            due = []
            for item in items:
                if item.schedule_seconds is None:
                    continue
                if item.last_run_at is None:
                    due.append(item)
                    continue
                if item.last_run_at <= now - timedelta(seconds=item.schedule_seconds):
                    due.append(item)
            return [_to_monitor(item) for item in due]

    def mark_monitor_run(self, monitor_id: UUID, run_at: datetime | None = None) -> None:
        run_at = run_at or datetime.now(timezone.utc)
        with SessionLocal() as session:
            model = session.get(MonitorModel, str(monitor_id))
            if model:
                model.last_run_at = run_at
                session.commit()


STORE = DatabaseStore()
