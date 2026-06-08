"""Structured agent execution trace log API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.logging_config import AGENT_TRACE_LOG_FILENAME, get_agent_trace_log_dir, get_agent_trace_log_path

router = APIRouter(prefix="/logs", tags=["logs"])
security = HTTPBearer()


async def get_current_trace_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Resolve the current JWT user while keeping this module import-light for tests."""
    from app.database import async_session
    from app.core.security import get_current_user

    async with async_session() as db:
        return await get_current_user(credentials, db)


def _candidate_trace_files() -> list[Path]:
    log_dir = get_agent_trace_log_dir()
    files = []
    active = get_agent_trace_log_path()
    if active.exists():
        files.append(active)
    if log_dir.exists():
        files.extend(
            path
            for path in log_dir.glob(f"{AGENT_TRACE_LOG_FILENAME}*")
            if path.is_file() and path != active
        )
    return sorted(set(files), key=lambda path: path.stat().st_mtime)


def _flatten_loguru_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    record = raw.get("record")
    if not isinstance(record, dict):
        return None
    extra = record.get("extra") or {}
    if not isinstance(extra, dict):
        extra = {}
    time_payload = record.get("time") or {}
    level_payload = record.get("level") or {}
    return {
        "timestamp": time_payload.get("timestamp") if isinstance(time_payload, dict) else None,
        "time": time_payload.get("repr") if isinstance(time_payload, dict) else None,
        "level": level_payload.get("name") if isinstance(level_payload, dict) else None,
        "message": record.get("message"),
        **extra,
    }


def read_agent_trace_entries(
    *,
    trace_id: str | None = None,
    act: str | None = "agent_loop",
    task_id: str | None = None,
    agent_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Read structured trace entries from the JSONL sink."""
    matches: list[dict[str, Any]] = []
    for path in _candidate_trace_files():
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = _flatten_loguru_record(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                    if not entry:
                        continue
                    if act and entry.get("act") != act:
                        continue
                    if trace_id and entry.get("trace_id") != trace_id:
                        continue
                    if task_id and str(entry.get("task_id") or "") != task_id:
                        continue
                    if agent_id and str(entry.get("agent_id") or "") != agent_id:
                        continue
                    matches.append(entry)
        except OSError:
            continue

    matches.sort(key=lambda item: item.get("timestamp") or 0)
    return matches[-limit:]


@router.get("/agent-trace")
async def get_agent_trace(
    trace_id: Optional[str] = Query(None),
    act: str = Query("agent_loop"),
    task_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    current_user=Depends(get_current_trace_user),
):
    """Query structured agent loop logs by trace_id, task_id, or agent_id."""
    _ = current_user
    if not trace_id and not task_id and not agent_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="trace_id, task_id, or agent_id is required",
        )
    return read_agent_trace_entries(
        trace_id=trace_id,
        act=act,
        task_id=task_id,
        agent_id=agent_id,
        limit=limit,
    )
