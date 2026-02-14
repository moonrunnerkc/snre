# Author: Bradley R. Kinnard
"""
SwarmCoordinator -- orchestrates agent lifecycle, session management,
and the iterative refactoring loop.

Dependencies injected explicitly: registry, repository, consensus, tracker, recorder.
Event hook: on_step_complete callback decouples recorder from coordinator.
Agents run in parallel via asyncio.to_thread (CPU-bound libcst work).
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Optional
from uuid import UUID

import structlog
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram

from snre.adapters.repository import SessionRepository
from snre.agents.protocol import RefactoringAgent
from snre.agents.registry import AgentRegistry
from snre.core.tracker import ChangeTracker
from snre.errors import AgentNotFoundError
from snre.errors import InvalidPathError
from snre.errors import SessionNotFoundError
from snre.models.changes import Change
from snre.models.changes import ConsensusDecision
from snre.models.config import SNREConfig
from snre.models.enums import RefactorStatus
from snre.models.session import EvolutionStep
from snre.models.session import RefactorSession

logger = structlog.get_logger(__name__)

# re-export for bind/unbind in async loop
_bind_contextvars = structlog.contextvars.bind_contextvars
_unbind_contextvars = structlog.contextvars.unbind_contextvars

REFACTOR_SESSIONS_TOTAL = Counter(
    "snre_refactor_sessions_total", "total sessions started"
)
AGENT_LATENCY = Histogram(
    "snre_agent_latency_seconds",
    "agent execution time",
    ["agent_id"],
)
ACTIVE_SESSIONS = Gauge("snre_active_sessions", "currently active sessions")
CONSENSUS_ROUNDS = Counter("snre_consensus_rounds_total", "total consensus rounds")


class SwarmCoordinator:
    """Coordinates multiple agents in refactoring process. All deps injected."""

    def __init__(
        self,
        config: SNREConfig,
        registry: AgentRegistry,
        repository: SessionRepository,
        tracker: ChangeTracker,
        consensus_fn: Callable[[dict[str, dict[str, float]], float], ConsensusDecision],
        on_step_complete: Optional[Callable[[EvolutionStep], None]] = None,
    ) -> None:
        self.config = config
        self.registry = registry
        self.repository = repository
        self.tracker = tracker
        self._consensus_fn = consensus_fn
        self._on_step_complete = on_step_complete or (lambda step: None)
        self.active_sessions: dict[UUID, RefactorSession] = {}

    # ---- public API ----

    def register_agent(self, agent: RefactoringAgent) -> None:
        """Register an agent with the swarm (delegates to registry)."""
        self.registry.register(agent)

    def start_refactor(
        self,
        target_path: str,
        agent_set: list[str],
        config_overrides: Optional[dict[str, Any]] = None,
    ) -> UUID:
        """Start a new refactoring session. Runs async loop internally."""
        for agent_id in agent_set:
            if agent_id not in self.registry:
                raise AgentNotFoundError(agent_id)

        session_id = uuid.uuid4()

        try:
            with open(target_path, encoding="utf-8") as fh:
                original_code = fh.read()
        except FileNotFoundError:
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
        self.repository.save(session)
        REFACTOR_SESSIONS_TOTAL.inc()
        ACTIVE_SESSIONS.inc()

        # run the async loop; if we're already inside an event loop, schedule it
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # called from async context -- caller must await start_refactor_async
            asyncio.ensure_future(self._execute_refactoring(session_id))
        else:
            asyncio.run(self._execute_refactoring(session_id))

        return session_id

    async def start_refactor_async(
        self,
        target_path: str,
        agent_set: list[str],
        config_overrides: Optional[dict[str, Any]] = None,
    ) -> UUID:
        """Async entrypoint for starting refactoring from async contexts (API)."""
        for agent_id in agent_set:
            if agent_id not in self.registry:
                raise AgentNotFoundError(agent_id)

        session_id = uuid.uuid4()

        try:
            with open(target_path, encoding="utf-8") as fh:
                original_code = fh.read()
        except FileNotFoundError:
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
        self.repository.save(session)
        await self._execute_refactoring(session_id)
        return session_id

    def get_session_status(self, refactor_id: UUID) -> dict[str, Any]:
        session = self._ensure_loaded(refactor_id)
        return {
            "status": session.status.value,
            "progress": session.progress,
            "current_iteration": len(session.evolution_history),
            "agent_votes": {},
            "last_update": session.started_at.isoformat(),
        }

    def get_session_result(self, refactor_id: UUID) -> RefactorSession:
        return self._ensure_loaded(refactor_id)

    def cancel_session(self, refactor_id: UUID) -> bool:
        try:
            session = self._ensure_loaded(refactor_id)
        except SessionNotFoundError:
            return False
        session.status = RefactorStatus.CANCELLED
        session.completed_at = datetime.now()
        self.repository.save(session)
        return True

    def list_active_sessions(self) -> list[dict[str, Any]]:
        return [
            {
                "refactor_id": str(s.refactor_id),
                "target_path": s.target_path,
                "status": s.status.value,
                "started_at": s.started_at.isoformat(),
            }
            for s in self.active_sessions.values()
            if s.status in (RefactorStatus.STARTED, RefactorStatus.IN_PROGRESS)
        ]

    # ---- internals ----

    def _ensure_loaded(self, refactor_id: UUID) -> RefactorSession:
        """Load session from memory or repository."""
        if refactor_id in self.active_sessions:
            return self.active_sessions[refactor_id]
        session = self.repository.load(refactor_id)
        self.active_sessions[refactor_id] = session
        return session

    async def _execute_refactoring(self, session_id: UUID) -> None:
        """Async refactoring loop. Agents run in parallel via asyncio.to_thread."""
        _bind_contextvars(session_id=str(session_id))
        session = self.active_sessions[session_id]
        session.status = RefactorStatus.IN_PROGRESS
        self.repository.save(session)

        sem = asyncio.Semaphore(self.config.max_concurrent_agents)

        async def _run_agent_suggest(agent_id: str, code: str) -> list[Change]:
            async with sem:
                agent = self.registry.get(agent_id)
                import time

                t0 = time.monotonic()
                result = await asyncio.to_thread(agent.suggest_changes, code)
                AGENT_LATENCY.labels(agent_id=agent_id).observe(time.monotonic() - t0)
                return result

        try:
            current_code = session.original_code
            consecutive_stalls = 0
            last_snapshot = current_code

            for iteration in range(self.config.max_iterations):
                session.progress = int((iteration / self.config.max_iterations) * 100)
                if iteration % 2 == 0:
                    self.repository.save(session)

                # gather suggestions from all agents in parallel
                tasks = [
                    _run_agent_suggest(aid, current_code) for aid in session.agent_set
                ]
                results = await asyncio.gather(*tasks)
                all_changes: list[Change] = [c for batch in results for c in batch]

                if not all_changes:
                    logger.info("convergence.no_changes", iteration=iteration)
                    break

                # filter out no-ops
                meaningful = self._filter_meaningful(all_changes, current_code)
                if not meaningful:
                    consecutive_stalls += 1
                    if consecutive_stalls >= 3:
                        logger.info("convergence.stalled", stalls=3)
                        break
                    continue
                else:
                    consecutive_stalls = 0

                # consensus vote (agents vote in parallel too)
                _meaningful = meaningful  # bind loop var for closure

                async def _run_vote(
                    aid: str, changes: list[Change] = _meaningful
                ) -> tuple[str, dict[str, float]]:
                    async with sem:
                        agent = self.registry.get(aid)
                        votes = await asyncio.to_thread(agent.vote, changes)
                        return aid, votes

                vote_tasks = [_run_vote(aid) for aid in session.agent_set]
                vote_results = await asyncio.gather(*vote_tasks)
                votes = dict(vote_results)

                decision = self._consensus_fn(votes, self.config.consensus_threshold)
                CONSENSUS_ROUNDS.inc()
                session.consensus_log.append(decision)

                # apply best change above threshold
                best = max(meaningful, key=lambda c: c.confidence)
                if best.confidence >= self.config.consensus_threshold:
                    new_code = self._apply_change(current_code, best)
                    if new_code != current_code:
                        current_code = new_code
                        step = EvolutionStep(
                            iteration=iteration,
                            timestamp=datetime.now(),
                            agent=best.agent_id,
                            change_type=best.change_type,
                            confidence=best.confidence,
                            description=best.description,
                            code_diff=(f"-{best.original_code}\n+{best.modified_code}"),
                        )
                        session.evolution_history.append(step)
                        self._on_step_complete(step)
                        logger.info(
                            "refactoring.step_applied",
                            iteration=iteration,
                            agent=best.agent_id,
                            confidence=best.confidence,
                        )

                # stall detection
                if current_code == last_snapshot:
                    consecutive_stalls += 1
                    if consecutive_stalls >= 3:
                        logger.info("convergence.unchanged", stalls=3)
                        break
                else:
                    last_snapshot = current_code
                    consecutive_stalls = 0

            session.refactored_code = current_code
            session.progress = 100
            session.status = RefactorStatus.COMPLETED
            session.completed_at = datetime.now()
            session.metrics = self.tracker.calculate_metrics(
                session.original_code, session.refactored_code
            )
            logger.info(
                "refactoring.completed",
                changes=len(session.evolution_history),
            )

        except Exception as exc:
            session.status = RefactorStatus.FAILED
            session.error_message = str(exc)
            session.completed_at = datetime.now()
            logger.error("refactoring.failed", error=str(exc))

        finally:
            ACTIVE_SESSIONS.dec()
            _unbind_contextvars("session_id")
            self.repository.save(session)

    def _filter_meaningful(
        self, changes: list[Change], current_code: str
    ) -> list[Change]:
        """Drop changes that wouldn't actually modify the code."""
        lines = current_code.split("\n")
        result = []
        for c in changes:
            if 0 <= c.line_start < len(lines):
                if lines[c.line_start].strip() != c.modified_code.strip():
                    result.append(c)
        return result

    def _apply_change(self, code: str, change: Change) -> str:
        """Apply a single line-level change."""
        lines = code.split("\n")
        if 0 <= change.line_start < len(lines):
            if lines[change.line_start].strip() == change.original_code.strip():
                lines[change.line_start] = change.modified_code
            else:
                logger.warning(
                    "line_mismatch",
                    line=change.line_start,
                    expected=change.original_code.strip(),
                    got=lines[change.line_start].strip(),
                )
        return "\n".join(lines)
