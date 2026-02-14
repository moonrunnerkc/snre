# Author: Bradley R. Kinnard
"""
Session, evolution step, and metrics models.
"""

from datetime import datetime
from typing import Any
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from snre.models.changes import ConsensusDecision
from snre.models.enums import ChangeType
from snre.models.enums import RefactorStatus


class EvolutionStep(BaseModel):
    """Single step in evolution history."""

    iteration: int
    timestamp: datetime
    agent: str
    change_type: ChangeType
    confidence: float
    description: str
    code_diff: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvolutionStep":
        return cls.model_validate(data)


class RefactorMetrics(BaseModel):
    """Metrics for a completed refactoring run."""

    lines_changed: int
    complexity_delta: float
    security_improvements: int
    performance_gains: float
    agent_contributions: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RefactorMetrics":
        return cls.model_validate(data)


class RefactorSession(BaseModel):
    """Complete refactoring session state."""

    refactor_id: UUID
    target_path: str
    status: RefactorStatus
    progress: int
    agent_set: list[str]
    original_code: str
    refactored_code: Optional[str] = None
    evolution_history: list[EvolutionStep] = []
    consensus_log: list[ConsensusDecision] = []
    metrics: Optional[RefactorMetrics] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RefactorSession":
        return cls.model_validate(data)
