# Author: Bradley R. Kinnard
"""
Change, AgentAnalysis, and ConsensusDecision models.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from snre.models.enums import ChangeType


class Change(BaseModel):
    """A single code change suggestion from an agent."""

    agent_id: str
    change_type: ChangeType
    original_code: str
    modified_code: str
    line_start: int
    line_end: int
    confidence: float
    description: str
    impact_score: float

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict. backward compat wrapper around model_dump."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Change":
        """Reconstruct from dict. backward compat wrapper around model_validate."""
        return cls.model_validate(data)


class AgentAnalysis(BaseModel):
    """Result of agent code analysis."""

    agent_id: str
    issues_found: int
    complexity_score: float
    security_risks: list[str]
    optimization_opportunities: list[str]
    confidence: float


class ConsensusDecision(BaseModel):
    """Record of consensus voting."""

    timestamp: datetime
    decision: str
    votes: dict[str, dict[str, float]]
    winning_agent: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConsensusDecision":
        return cls.model_validate(data)
