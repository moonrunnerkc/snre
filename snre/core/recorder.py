# Author: Bradley R. Kinnard
"""
Evolution recorder -- persists snapshots and step history.
Subscribes to coordinator events via on_step_complete callback.
"""

import json
import os
from datetime import datetime
from datetime import timedelta
from uuid import UUID

import structlog

from snre.models.changes import Change
from snre.models.config import SNREConfig
from snre.models.session import EvolutionStep

logger = structlog.get_logger(__name__)


class EvolutionRecorder:
    """Records evolution history and snapshots to disk."""

    def __init__(self, config: SNREConfig) -> None:
        self.config = config
        self.snapshots_dir = config.snapshots_dir
        self.logs_dir = config.logs_dir

        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

    def record_step(self, session_id: UUID, step: EvolutionStep) -> None:
        """Append a step to the session log file."""
        log_file = os.path.join(self.logs_dir, f"{session_id}.json")

        try:
            with open(log_file, encoding="utf-8") as fh:
                log_data = json.load(fh)
        except FileNotFoundError:
            log_data = {"session_id": str(session_id), "steps": []}

        log_data["steps"].append(step.to_dict())

        with open(log_file, "w", encoding="utf-8") as fh:
            json.dump(log_data, fh, indent=2, ensure_ascii=False)

    def create_snapshot(self, session_id: UUID, code: str, iteration: int) -> str:
        """Write a code snapshot at the configured frequency."""
        if not self.config.enable_evolution_log:
            return ""
        if iteration % self.config.snapshot_frequency != 0:
            return ""

        snapshot_file = os.path.join(
            self.snapshots_dir, f"{session_id}_iter_{iteration}.py"
        )
        with open(snapshot_file, "w", encoding="utf-8") as fh:
            fh.write(
                f"# SNRE Snapshot - Session: {session_id}, Iteration: {iteration}\n"
            )
            fh.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            fh.write(code)
        return snapshot_file

    def create_evolution_step(self, iteration: int, change: Change) -> EvolutionStep:
        """Build an EvolutionStep from a Change."""
        return EvolutionStep(
            iteration=iteration,
            timestamp=datetime.now(),
            agent=change.agent_id,
            change_type=change.change_type,
            confidence=change.confidence,
            description=change.description,
            code_diff=(
                f"@@ -{change.line_start},{change.line_end} "
                f"+{change.line_start},{change.line_end} @@\n"
                f"-{change.original_code}\n+{change.modified_code}"
            ),
        )

    def cleanup_old_snapshots(self) -> None:
        """Remove snapshots older than 30 days or beyond max_snapshots."""
        if not os.path.exists(self.snapshots_dir):
            return

        cutoff = datetime.now() - timedelta(days=30)
        for fname in os.listdir(self.snapshots_dir):
            fpath = os.path.join(self.snapshots_dir, fname)
            try:
                if datetime.fromtimestamp(os.path.getmtime(fpath)) < cutoff:
                    os.remove(fpath)
            except OSError:
                continue

        snapshot_files = sorted(
            [f for f in os.listdir(self.snapshots_dir) if f.endswith(".py")],
            key=lambda f: os.path.getmtime(os.path.join(self.snapshots_dir, f)),
        )
        if len(snapshot_files) > self.config.max_snapshots:
            for fname in snapshot_files[: -self.config.max_snapshots]:
                try:
                    os.remove(os.path.join(self.snapshots_dir, fname))
                except OSError:
                    continue
