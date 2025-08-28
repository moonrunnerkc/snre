"""
Evolution recording and snapshot management for SNRE
"""

import json
import os
from datetime import datetime, timedelta
from uuid import UUID

from contracts import Change, Config, EvolutionStep


class EvolutionRecorder:
    """Records evolution history and snapshots"""

    def __init__(self, config: Config):
        self.config = config
        self.snapshots_dir = "data/snapshots"
        self.logs_dir = "data/refactor_logs"
        self.sessions_dir = "data/refactor_logs/sessions"

        # Ensure directories exist
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.sessions_dir, exist_ok=True)

    def record_step(self, session_id: UUID, step: EvolutionStep) -> None:
        """Record a single evolution step"""
        log_file = os.path.join(self.logs_dir, f"{session_id}.json")

        # Load existing log or create new
        try:
            with open(log_file, encoding='utf-8') as f:
                log_data = json.load(f)
        except FileNotFoundError:
            log_data = {"session_id": str(session_id), "steps": []}

        # Add new step using the step's serialization method
        step_data = step.to_dict()
        log_data["steps"].append(step_data)

        # Write back to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def create_snapshot(self, session_id: UUID, code: str, iteration: int) -> str:
        """Create code snapshot for iteration"""
        if not self.config.enable_evolution_log:
            return ""

        # Create snapshot only at specified frequency
        if iteration % self.config.snapshot_frequency != 0:
            return ""

        snapshot_file = os.path.join(
            self.snapshots_dir,
            f"{session_id}_iter_{iteration}.py"
        )

        with open(snapshot_file, 'w', encoding='utf-8') as f:
            f.write(f"# SNRE Snapshot - Session: {session_id}, Iteration: {iteration}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            f.write(code)

        return snapshot_file

    def get_evolution_history(self, session_id: UUID) -> list[EvolutionStep]:
        """Get complete evolution history for session"""
        log_file = os.path.join(self.logs_dir, f"{session_id}.json")

        try:
            with open(log_file, encoding='utf-8') as f:
                log_data = json.load(f)

            steps = []
            for step_data in log_data.get("steps", []):
                # Use the EvolutionStep's deserialization method
                step = EvolutionStep.from_dict(step_data)
                steps.append(step)

            return steps

        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Warning: Failed to load evolution history for {session_id}: {e}")
            return []

    def cleanup_old_snapshots(self) -> None:
        """Clean up old snapshots based on retention policy"""
        if not os.path.exists(self.snapshots_dir):
            return

        cutoff_date = datetime.now() - timedelta(days=30)

        for filename in os.listdir(self.snapshots_dir):
            file_path = os.path.join(self.snapshots_dir, filename)

            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_date:
                    os.remove(file_path)
            except OSError:
                continue

        # Also limit total number of snapshots
        snapshot_files = [
            f for f in os.listdir(self.snapshots_dir)
            if f.endswith('.py')
        ]

        if len(snapshot_files) > self.config.max_snapshots:
            # Sort by modification time and remove oldest
            snapshot_files.sort(
                key=lambda f: os.path.getmtime(os.path.join(self.snapshots_dir, f))
            )

            files_to_remove = snapshot_files[:-self.config.max_snapshots]
            for filename in files_to_remove:
                try:
                    os.remove(os.path.join(self.snapshots_dir, filename))
                except OSError:
                    continue

    def create_evolution_step(self, iteration: int, change: Change) -> EvolutionStep:
        """Create evolution step from change"""
        return EvolutionStep(
            iteration=iteration,
            timestamp=datetime.now(),
            agent=change.agent_id,
            change_type=change.change_type,
            confidence=change.confidence,
            description=change.description,
            code_diff=f"@@ -{change.line_start},{change.line_end} +{change.line_start},{change.line_end} @@\n-{change.original_code}\n+{change.modified_code}"
        )

    def get_session_snapshots(self, session_id: UUID) -> list[str]:
        """Get all snapshot files for a session"""
        if not os.path.exists(self.snapshots_dir):
            return []

        session_snapshots = []
        session_prefix = f"{session_id}_iter_"

        for filename in os.listdir(self.snapshots_dir):
            if filename.startswith(session_prefix) and filename.endswith('.py'):
                session_snapshots.append(os.path.join(self.snapshots_dir, filename))

        # Sort by iteration number
        session_snapshots.sort(key=lambda f: self._extract_iteration_from_filename(f))
        return session_snapshots

    def _extract_iteration_from_filename(self, filepath: str) -> int:
        """Extract iteration number from snapshot filename"""
        try:
            filename = os.path.basename(filepath)
            # Extract number between 'iter_' and '.py'
            start = filename.find('iter_') + 5
            end = filename.rfind('.py')
            return int(filename[start:end])
        except (ValueError, AttributeError):
            return 0

    def cleanup_session_files(self, session_id: UUID) -> None:
        """Clean up all files associated with a session"""
        # Clean up snapshots
        session_snapshots = self.get_session_snapshots(session_id)
        for snapshot_path in session_snapshots:
            try:
                os.remove(snapshot_path)
            except OSError:
                continue

        # Clean up evolution log
        log_file = os.path.join(self.logs_dir, f"{session_id}.json")
        try:
            if os.path.exists(log_file):
                os.remove(log_file)
        except OSError:
            pass

        # Note: We don't clean up the session file itself from sessions_dir
        # That's handled by SwarmCoordinator if needed
