# Author: Bradley R. Kinnard
"""
SNRE error hierarchy. One file, one concern.
"""

from typing import Any
from typing import Optional


class SNREError(Exception):
    """Base exception for SNRE errors."""

    def __init__(
        self, code: str, message: str, details: Optional[dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class InvalidPathError(SNREError):
    """Target path does not exist or is not accessible."""

    def __init__(self, path: str):
        super().__init__("INVALID_PATH", f"Invalid target path: {path}")


class AgentNotFoundError(SNREError):
    """Requested agent is not available."""

    def __init__(self, agent_id: str):
        super().__init__("AGENT_NOT_FOUND", f"Agent not found: {agent_id}")


class SessionNotFoundError(SNREError):
    """Refactor ID does not exist."""

    def __init__(self, session_id: str):
        super().__init__("SESSION_NOT_FOUND", f"Session not found: {session_id}")


class ConsensusFailedError(SNREError):
    """Agents could not reach consensus."""

    def __init__(self, details: dict[str, Any]):
        super().__init__(
            "CONSENSUS_FAILED", "Agents failed to reach consensus", details
        )


class SNRESyntaxError(SNREError):
    """Code parsing failed."""

    def __init__(self, details: str):
        super().__init__("SYNTAX_ERROR", f"Syntax error: {details}")


class TimeoutError(SNREError):
    """Refactoring session timed out."""

    def __init__(self, session_id: str):
        super().__init__("TIMEOUT", f"Session {session_id} timed out")


class PermissionDeniedError(SNREError):
    """Insufficient permissions for target path."""

    def __init__(self, path: str):
        super().__init__("PERMISSION_DENIED", f"Permission denied: {path}")
