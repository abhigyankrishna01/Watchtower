from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas import CheckResult, Monitor, MonitorCreate, MonitorList, ResultList, RunRequest
from app.core.auth import require_auth
from app.scheduler.scheduler import run_monitor
from app.services.storage import STORE

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/monitors", response_model=Monitor, dependencies=[Depends(require_auth)])
async def create_monitor(payload: MonitorCreate) -> Monitor:
    monitor = Monitor(**payload.model_dump())
    STORE.add_monitor(monitor)
    return monitor


@router.get("/monitors", response_model=MonitorList, dependencies=[Depends(require_auth)])
async def list_monitors() -> MonitorList:
    return MonitorList(monitors=STORE.list_monitors())


@router.post("/monitors/{monitor_id}/run", response_model=CheckResult | None, dependencies=[Depends(require_auth)])
async def run_monitor_now(monitor_id: UUID, payload: RunRequest | None = None) -> CheckResult | None:
    monitor = STORE.get_monitor(monitor_id)
    if not monitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    return run_monitor(monitor, reason=(payload.reason if payload else None))


@router.get("/results", response_model=ResultList, dependencies=[Depends(require_auth)])
async def list_results(monitor_id: UUID | None = None) -> ResultList:
    return ResultList(results=STORE.list_results(monitor_id))
