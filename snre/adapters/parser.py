# Author: Bradley R. Kinnard
"""
CodeParser adapter -- libcst wrapper, lazy-loaded.
Isolates the libcst dependency so agents can import without requiring it at module level.
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# lazy import to avoid hard dep at module load
_cst = None


def _ensure_cst() -> Any:
    """Load libcst on first call."""
    global _cst
    if _cst is None:
        import libcst as cst
        _cst = cst
    return _cst


def parse_module(code: str) -> Any:
    """Parse Python source into a libcst Module tree."""
    cst = _ensure_cst()
    return cst.parse_module(code)


def detect_language(file_path: str) -> str:
    """Guess language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
    }
    ext = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
    return ext_map.get(ext, "unknown")
