# Author: Bradley R. Kinnard
"""
FastAPI application factory for SNRE.
App factory pattern -- no global app object. Testable with httpx.AsyncClient.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import generate_latest
from pydantic import BaseModel
from pydantic import Field

from snre.errors import AgentNotFoundError
from snre.errors import InvalidPathError
from snre.errors import SessionNotFoundError

logger = structlog.get_logger(__name__)


# ---- request / response schemas ----


class StartRefactorRequest(BaseModel):
    target_path: str
    agent_set: list[str] = Field(default_factory=list)
    config_overrides: dict[str, Any] = Field(default_factory=dict)


class StartRefactorResponse(BaseModel):
    refactor_id: str
    status: str
    timestamp: str
    agents_loaded: list[str]


class SessionStatusResponse(BaseModel):
    status: str
    progress: int
    current_iteration: int
    agent_votes: dict[str, Any]
    last_update: str


class ErrorResponse(BaseModel):
    code: str
    message: str


# ---- app factory ----


def create_app(coordinator: Any) -> FastAPI:
    """Build a FastAPI app wired to the given coordinator."""
    app = FastAPI(title="SNRE", version="1.0.0")

    @app.post("/refactor/start", response_model=StartRefactorResponse)
    async def start_refactor(request: StartRefactorRequest) -> StartRefactorResponse:
        try:
            session_id = await coordinator.start_refactor_async(
                request.target_path,
                request.agent_set,
                request.config_overrides or None,
            )
            return StartRefactorResponse(
                refactor_id=str(session_id),
                status="started",
                timestamp=datetime.now().isoformat(),
                agents_loaded=request.agent_set,
            )
        except AgentNotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message)
        except InvalidPathError as exc:
            raise HTTPException(status_code=400, detail=exc.message)

    @app.get("/refactor/status/{refactor_id}")
    def get_status(refactor_id: str) -> dict[str, Any]:
        try:
            sid = UUID(refactor_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid session id format")
        try:
            return coordinator.get_session_status(sid)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message)

    @app.get("/refactor/result/{refactor_id}")
    def get_result(refactor_id: str) -> dict[str, Any]:
        try:
            sid = UUID(refactor_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid session id format")
        try:
            session = coordinator.get_session_result(sid)
            return session.to_dict()
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message)

    @app.get("/refactor/sessions")
    def list_sessions() -> dict[str, Any]:
        return {"active_sessions": coordinator.list_active_sessions()}

    @app.delete("/refactor/session/{refactor_id}")
    def cancel_session(refactor_id: str) -> dict[str, Any]:
        try:
            sid = UUID(refactor_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid session id format")

        success = coordinator.cancel_session(sid)
        if not success:
            raise HTTPException(status_code=400, detail="failed to cancel session")

        return {
            "refactor_id": refactor_id,
            "status": "cancelled",
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "healthy", "service": "SNRE"}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> PlainTextResponse:
        """Prometheus metrics endpoint."""
        return PlainTextResponse(
            content=generate_latest().decode("utf-8"),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app
