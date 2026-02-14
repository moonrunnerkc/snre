# Author: Bradley R. Kinnard
"""
Enums for refactoring sessions and change classification.
"""

from enum import Enum


class RefactorStatus(Enum):
    """session lifecycle states"""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChangeType(Enum):
    """categories of code changes agents can propose"""

    OPTIMIZATION = "optimization"
    SECURITY = "security"
    READABILITY = "readability"
    PERFORMANCE = "performance"
    STRUCTURE = "structure"
