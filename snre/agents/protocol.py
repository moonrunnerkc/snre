# Author: Bradley R. Kinnard
"""
RefactoringAgent Protocol -- structural typing for agents.
Any class matching this shape is a valid agent. No inheritance required.
"""

from typing import Protocol
from typing import runtime_checkable

from snre.models.changes import AgentAnalysis
from snre.models.changes import Change


@runtime_checkable
class RefactoringAgent(Protocol):
    """Structural contract every refactoring agent must satisfy."""

    agent_id: str

    def analyze(self, code: str) -> AgentAnalysis:
        ...

    def suggest_changes(self, code: str) -> list[Change]:
        ...

    def vote(self, changes: list[Change]) -> dict[str, float]:
        ...

    def validate_result(self, original: str, modified: str) -> bool:
        ...
