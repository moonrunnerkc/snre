# Author: Bradley R. Kinnard
"""
SessionRepository protocol with File and SQLite implementations.
Storage backend is selected via SNREConfig.storage_backend.
"""

import os
import sqlite3
from pathlib import Path
from typing import Protocol
from uuid import UUID

import structlog
from filelock import FileLock

from snre.errors import SessionNotFoundError
from snre.models.session import RefactorSession

logger = structlog.get_logger(__name__)


class SessionRepository(Protocol):
    """Structural contract for session persistence."""

    def save(self, session: RefactorSession) -> None: ...

    def load(self, session_id: UUID) -> RefactorSession: ...

    def list_active(self) -> list[UUID]: ...

    def delete(self, session_id: UUID) -> None: ...


class FileSessionRepository:
    """File-based session storage with filelock for safe concurrent access."""

    def __init__(self, sessions_dir: str) -> None:
        self._dir = sessions_dir
        os.makedirs(self._dir, exist_ok=True)

    def save(self, session: RefactorSession) -> None:
        """Persist session as JSON with file locking."""
        path = os.path.join(self._dir, f"{session.refactor_id}.json")
        lock = FileLock(f"{path}.lock")
        try:
            with lock:
                Path(path).write_text(
                    session.model_dump_json(indent=2), encoding="utf-8"
                )
        except Exception as exc:
            logger.warning("session.save_failed", session_id=str(session.refactor_id), error=str(exc))

    def load(self, session_id: UUID) -> RefactorSession:
        """Load session from JSON file. Raises SessionNotFoundError if missing."""
        path = os.path.join(self._dir, f"{session_id}.json")
        if not os.path.exists(path):
            raise SessionNotFoundError(str(session_id))

        lock = FileLock(f"{path}.lock")
        with lock:
            raw = Path(path).read_text(encoding="utf-8")
        return RefactorSession.model_validate_json(raw)

    def load_or_none(self, session_id: UUID) -> RefactorSession | None:
        """Load session, returning None instead of raising on miss."""
        try:
            return self.load(session_id)
        except (SessionNotFoundError, Exception) as exc:
            logger.debug("session.load_miss", session_id=str(session_id), error=str(exc))
            return None

    def list_active(self) -> list[UUID]:
        """Return UUIDs of all sessions on disk."""
        result: list[UUID] = []
        if not os.path.exists(self._dir):
            return result

        for fname in os.listdir(self._dir):
            if not fname.endswith(".json"):
                continue
            try:
                result.append(UUID(fname[:-5]))
            except ValueError:
                continue
        return result

    def delete(self, session_id: UUID) -> None:
        """Remove a session file from disk."""
        path = os.path.join(self._dir, f"{session_id}.json")
        lock_path = f"{path}.lock"
        for p in (path, lock_path):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass


class SQLiteSessionRepository:
    """SQLite-backed session storage. Same SessionRepository protocol."""

    _DDL = """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        data TEXT NOT NULL
    )
    """

    def __init__(self, db_path: str = "data/snre.db") -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(self._DDL)

    def save(self, session: RefactorSession) -> None:
        """Upsert session as JSON blob."""
        json_data = session.model_dump_json(indent=2)
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO sessions (session_id, data) VALUES (?, ?)",
                    (str(session.refactor_id), json_data),
                )
        except sqlite3.Error as exc:
            logger.warning("session.sqlite_save_failed",
                           session_id=str(session.refactor_id), error=str(exc))

    def load(self, session_id: UUID) -> RefactorSession:
        """Load session by id. Raises SessionNotFoundError if missing."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM sessions WHERE session_id = ?",
                (str(session_id),),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(str(session_id))
        return RefactorSession.model_validate_json(row[0])

    def list_active(self) -> list[UUID]:
        """Return all stored session ids."""
        with self._connect() as conn:
            rows = conn.execute("SELECT session_id FROM sessions").fetchall()
        result: list[UUID] = []
        for (sid,) in rows:
            try:
                result.append(UUID(sid))
            except ValueError:
                continue
        return result

    def delete(self, session_id: UUID) -> None:
        """Remove a session from the database."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (str(session_id),),
            )
