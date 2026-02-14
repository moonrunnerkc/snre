# Author: Bradley R. Kinnard
"""
Agent profile configuration model.
"""

from typing import Any

from pydantic import BaseModel


class AgentProfile(BaseModel):
    """Configuration profile loaded from agent_profiles.yaml."""

    name: str
    priority: int
    enabled: bool
    patterns: list[str]
    confidence_threshold: float
    config: dict[str, Any]
