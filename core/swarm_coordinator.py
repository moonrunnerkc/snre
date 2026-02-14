"""
Swarm coordination system for SNRE
"""

import json
import os
import uuid
from datetime import datetime

# Import BaseAgent with TYPE_CHECKING to avoid circular import
from typing import TYPE_CHECKING
from typing import Any
from typing import Optional
from uuid import UUID

from filelock import FileLock

from snre.errors import AgentNotFoundError
from snre.errors import SessionNotFoundError
from snre.models.changes import Change
from snre.models.config import Config
from snre.models.enums import RefactorStatus
from snre.models.session import RefactorSession

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent

import logging

from .change_tracker import ChangeTracker
from .consensus_engine import ConsensusEngine
from .evolution_recorder import EvolutionRecorder

logger = logging.getLogger(__name__)


class SwarmCoordinator:
    """Coordinates multiple agents in refactoring process"""

    def __init__(self, config: Config):
        self.config = config
        self.agents: dict[str, "BaseAgent"] = {}
        self.active_sessions: dict[UUID, RefactorSession] = {}
        self.consensus_engine = ConsensusEngine(config)
        self.change_tracker = ChangeTracker(config)
        self.evolution_recorder = EvolutionRecorder(config)

        # Initialize session storage directory
        self.sessions_dir = "data/refactor_logs/sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)

        # Load existing sessions on startup
        self.load_all_sessions()

    def register_agent(self, agent: "BaseAgent") -> None:
        """Register an agent with the swarm"""
        self.agents[agent.agent_id] = agent

    def start_refactor(
        self,
        target_path: str,
        agent_set: list[str],
        config_overrides: Optional[dict[str, Any]] = None,
    ) -> UUID:
        """Start a new refactoring session"""
        # Validate agents exist
        for agent_id in agent_set:
            if agent_id not in self.agents:
                raise AgentNotFoundError(agent_id)

        # Create session
        session_id = uuid.uuid4()

        # Read target file
        try:
            with open(target_path, encoding="utf-8") as f:
                original_code = f.read()
        except FileNotFoundError:
            from snre.errors import InvalidPathError

            raise InvalidPathError(target_path)

        session = RefactorSession(
            refactor_id=session_id,
            target_path=target_path,
            status=RefactorStatus.STARTED,
            progress=0,
            agent_set=agent_set,
            original_code=original_code,
            refactored_code=None,
            evolution_history=[],
            consensus_log=[],
            metrics=None,
            started_at=datetime.now(),
            completed_at=None,
            error_message=None,
        )

        self.active_sessions[session_id] = session

        # Persist session immediately
        self.save_session(session)

        # Start async refactoring process
        self._execute_refactoring(session_id)

        return session_id

    def get_session_status(self, refactor_id: UUID) -> dict[str, Any]:
        """Get current status of refactoring session"""
        # Try to load from disk if not in memory
        if refactor_id not in self.active_sessions:
            loaded_session = self.load_session(refactor_id)
            if loaded_session:
                self.active_sessions[refactor_id] = loaded_session
            else:
                raise SessionNotFoundError(str(refactor_id))

        session = self.active_sessions[refactor_id]

        # Calculate agent votes summary
        agent_votes = {}
        for agent_id in session.agent_set:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent_votes[agent_id] = {
                    "score": 0.0,
                    "confidence": agent.get_confidence_threshold(),
                    "suggestions": 0,
                }

        return {
            "status": session.status.value,
            "progress": session.progress,
            "current_iteration": len(session.evolution_history),
            "agent_votes": agent_votes,
            "last_update": session.started_at.isoformat(),
        }

    def get_session_result(self, refactor_id: UUID) -> RefactorSession:
        """Get complete results of refactoring session"""
        # Try to load from disk if not in memory
        if refactor_id not in self.active_sessions:
            loaded_session = self.load_session(refactor_id)
            if loaded_session:
                self.active_sessions[refactor_id] = loaded_session
            else:
                raise SessionNotFoundError(str(refactor_id))

        return self.active_sessions[refactor_id]

    def cancel_session(self, refactor_id: UUID) -> bool:
        """Cancel an active refactoring session"""
        # Try to load from disk if not in memory
        if refactor_id not in self.active_sessions:
            loaded_session = self.load_session(refactor_id)
            if loaded_session:
                self.active_sessions[refactor_id] = loaded_session
            else:
                return False

        session = self.active_sessions[refactor_id]
        session.status = RefactorStatus.CANCELLED
        session.completed_at = datetime.now()

        # Persist the updated session
        self.save_session(session)

        return True

    def list_active_sessions(self) -> list[dict[str, Any]]:
        """List all active refactoring sessions"""
        # Load all sessions to get complete picture
        self.load_all_sessions()

        return [
            {
                "refactor_id": str(session.refactor_id),
                "target_path": session.target_path,
                "status": session.status.value,
                "started_at": session.started_at.isoformat(),
            }
            for session in self.active_sessions.values()
            if session.status in [RefactorStatus.STARTED, RefactorStatus.IN_PROGRESS]
        ]

    def save_session(self, session: RefactorSession) -> None:
        """Save session to persistent storage with file locking"""
        session_file = os.path.join(self.sessions_dir, f"{session.refactor_id}.json")
        lock = FileLock(f"{session_file}.lock")

        try:
            session_data = session.to_dict()
            with lock:
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("failed to save session %s: %s", session.refactor_id, e)

    def load_session(self, refactor_id: UUID) -> Optional[RefactorSession]:
        """Load session from persistent storage with file locking"""
        session_file = os.path.join(self.sessions_dir, f"{refactor_id}.json")

        if not os.path.exists(session_file):
            return None

        lock = FileLock(f"{session_file}.lock")
        try:
            with lock:
                with open(session_file, encoding="utf-8") as f:
                    session_data = json.load(f)

            return RefactorSession.from_dict(session_data)
        except Exception as e:
            logger.warning("failed to load session %s: %s", refactor_id, e)
            return None

    def load_all_sessions(self) -> None:
        """Load all sessions from persistent storage"""
        if not os.path.exists(self.sessions_dir):
            return

        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".json"):
                try:
                    session_id_str = filename[:-5]  # Remove .json extension
                    session_id = UUID(session_id_str)

                    # Only load if not already in memory
                    if session_id not in self.active_sessions:
                        session = self.load_session(session_id)
                        if session:
                            self.active_sessions[session_id] = session
                except Exception as e:
                    logger.warning("failed to load session from %s: %s", filename, e)
                    continue

    def _execute_refactoring(self, session_id: UUID) -> None:
        """Execute the refactoring process for a session"""
        session = self.active_sessions[session_id]
        session.status = RefactorStatus.IN_PROGRESS

        # Save the status update immediately
        self.save_session(session)

        try:
            current_code = session.original_code
            consecutive_no_change_iterations = 0
            last_code_state = current_code

            for iteration in range(self.config.max_iterations):
                session.progress = int((iteration / self.config.max_iterations) * 100)

                # Save progress updates periodically
                if iteration % 2 == 0:  # Save every other iteration to reduce I/O
                    self.save_session(session)

                # Collect suggestions from all agents based on CURRENT code state
                all_changes = []
                for agent_id in session.agent_set:
                    agent = self.agents[agent_id]
                    agent_changes = agent.suggest_changes(current_code)
                    all_changes.extend(agent_changes)

                # Check for convergence - no meaningful changes suggested
                if not all_changes:
                    logger.info(
                        "convergence reached: no more changes suggested at iteration %d",
                        iteration,
                    )
                    break

                # Filter out changes that wouldn't actually modify the code
                meaningful_changes = []
                for change in all_changes:
                    current_lines = current_code.split("\n")
                    if (
                        change.line_start < len(current_lines)
                        and current_lines[change.line_start] != change.modified_code
                    ):
                        meaningful_changes.append(change)

                if not meaningful_changes:
                    consecutive_no_change_iterations += 1
                    logger.debug(
                        "no meaningful changes at iteration %d (consecutive: %d)",
                        iteration,
                        consecutive_no_change_iterations,
                    )

                    # Exit if we've had several iterations with no meaningful changes
                    if consecutive_no_change_iterations >= 3:
                        logger.info(
                            "convergence reached: no meaningful changes for 3 consecutive iterations"
                        )
                        break
                    continue
                else:
                    consecutive_no_change_iterations = 0

                # Get consensus on meaningful changes
                decision = self.consensus_engine.calculate_consensus(
                    {
                        agent_id: self.agents[agent_id].vote(meaningful_changes)
                        for agent_id in session.agent_set
                    }
                )

                session.consensus_log.append(decision)

                # Apply highest confidence change
                if meaningful_changes:
                    best_change = max(meaningful_changes, key=lambda c: c.confidence)
                    if best_change.confidence >= self.config.consensus_threshold:
                        new_code = self._apply_change(current_code, best_change)

                        # Verify the change actually modified the code
                        if new_code != current_code:
                            current_code = new_code

                            # Record evolution step
                            step = self.evolution_recorder.create_evolution_step(
                                iteration, best_change
                            )
                            session.evolution_history.append(step)

                            logger.info(
                                "applied change at iteration %d: %s",
                                iteration,
                                best_change.description,
                            )
                        else:
                            logger.debug(
                                "change did not modify code at iteration %d", iteration
                            )
                    else:
                        logger.debug(
                            "best change confidence (%.2f) below threshold (%.2f)",
                            best_change.confidence,
                            self.config.consensus_threshold,
                        )

                # Check if code hasn't changed for several iterations
                if current_code == last_code_state:
                    consecutive_no_change_iterations += 1
                    if consecutive_no_change_iterations >= 3:
                        logger.info(
                            "convergence reached: code unchanged for 3 consecutive iterations"
                        )
                        break
                else:
                    last_code_state = current_code
                    consecutive_no_change_iterations = 0

            session.refactored_code = current_code
            session.progress = 100
            session.status = RefactorStatus.COMPLETED
            session.completed_at = datetime.now()

            # Calculate final metrics
            session.metrics = self.change_tracker.calculate_metrics(
                session.original_code, session.refactored_code
            )

            logger.info(
                "refactoring completed after %d changes", len(session.evolution_history)
            )

        except Exception as e:
            session.status = RefactorStatus.FAILED
            session.error_message = str(e)
            session.completed_at = datetime.now()
            logger.error("refactoring failed: %s", e)

        finally:
            # Always save final session state
            self.save_session(session)

    def _apply_change(self, code: str, change: Change) -> str:
        """Apply a single change to code"""
        lines = code.split("\n")

        # Simple line replacement with bounds checking
        if 0 <= change.line_start < len(lines):
            # Only apply change if the original line matches what we expect
            if lines[change.line_start].strip() == change.original_code.strip():
                lines[change.line_start] = change.modified_code
            else:
                logger.warning(
                    "line %d doesn't match expected original, expected: '%s', actual: '%s'",
                    change.line_start,
                    change.original_code.strip(),
                    lines[change.line_start].strip(),
                )
        else:
            logger.warning(
                "line %d out of range (max: %d)", change.line_start, len(lines) - 1
            )

        return "\n".join(lines)

    def apply_session_to_file(
        self, refactor_id: UUID, create_backup: bool = True
    ) -> bool:
        """Apply refactored code from session to the original file"""
        try:
            # Get the session
            session = self.get_session_result(refactor_id)

            if session.status != RefactorStatus.COMPLETED:
                logger.warning(
                    "cannot apply: session status is %s", session.status.value
                )
                return False

            if not session.refactored_code:
                logger.warning("no refactored code available to apply")
                return False

            target_path = session.target_path

            # Create backup if requested
            if create_backup:
                import shutil

                backup_path = f"{target_path}.backup"
                try:
                    shutil.copy2(target_path, backup_path)
                except Exception as e:
                    logger.warning("could not create backup: %s", e)

            # Write refactored code to original file
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(session.refactored_code)

            return True

        except Exception as e:
            logger.error("error applying changes: %s", e)
            return False

    def show_session_diff(self, refactor_id: UUID) -> Optional[str]:
        """Get diff between original and refactored code"""
        try:
            session = self.get_session_result(refactor_id)

            if not session.refactored_code:
                return None

            return self.change_tracker.create_diff(
                session.original_code, session.refactored_code
            )

        except Exception:
            return None
