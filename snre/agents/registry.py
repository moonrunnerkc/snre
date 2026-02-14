# Author: Bradley R. Kinnard
"""
AgentRegistry -- discovers, holds, and validates agent instances.
Supports both builtin agents and third-party plugins via entry points.
"""

import importlib.metadata
from typing import Any

import structlog
import yaml

from snre.agents.protocol import RefactoringAgent
from snre.errors import AgentNotFoundError
from snre.models.config import SNREConfig

logger = structlog.get_logger(__name__)

ENTRY_POINT_GROUP = "snre.agents"


class AgentRegistry:
    """Discovers and holds agent instances. Validates Protocol conformance on register."""

    def __init__(self) -> None:
        self._agents: dict[str, RefactoringAgent] = {}

    def register(self, agent: RefactoringAgent) -> None:
        """Register an agent. Rejects anything that doesn't satisfy the Protocol."""
        if not isinstance(agent, RefactoringAgent):
            raise TypeError(
                f"{type(agent).__name__} does not satisfy RefactoringAgent protocol"
            )
        self._agents[agent.agent_id] = agent
        logger.info("agent.registered", agent_id=agent.agent_id)

    def get(self, agent_id: str) -> RefactoringAgent:
        """Fetch a registered agent by id. Raises AgentNotFoundError if missing."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(agent_id)
        return self._agents[agent_id]

    def all(self) -> dict[str, RefactoringAgent]:
        """Return a shallow copy of the agent registry."""
        return dict(self._agents)

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents

    @classmethod
    def from_profiles(
        cls, profiles_path: str, config: SNREConfig
    ) -> "AgentRegistry":
        """Load agent_profiles.yaml, instantiate and register all enabled agents.

        Discovery order: builtin agents first, then entry point plugins.
        Plugins that collide with a builtin id are skipped with a warning.
        """
        registry = cls()

        with open(profiles_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        agent_classes = _builtin_agent_map()

        # merge in plugins discovered via entry points
        for ep in importlib.metadata.entry_points(group=ENTRY_POINT_GROUP):
            if ep.name in agent_classes:
                logger.warning("plugin.shadowed_by_builtin",
                               plugin=ep.name, module=ep.value)
                continue
            try:
                agent_classes[ep.name] = ep.load()
                logger.info("plugin.discovered", agent_id=ep.name)
            except Exception as exc:
                logger.warning("plugin.load_failed", agent_id=ep.name, error=str(exc))

        for agent_id, profile in data.get("agents", {}).items():
            if not profile.get("enabled", False):
                logger.debug("agent.skipped_disabled", agent_id=agent_id)
                continue

            if agent_id not in agent_classes:
                logger.warning("agent.no_implementation", agent_id=agent_id)
                continue

            agent_cls = agent_classes[agent_id]
            agent = agent_cls(agent_id, config)

            # apply profile overrides
            if hasattr(agent, "_priority"):
                agent._priority = profile.get("priority", agent._priority)
            if hasattr(agent, "_confidence_threshold"):
                agent._confidence_threshold = profile.get(
                    "confidence_threshold", agent._confidence_threshold
                )

            registry.register(agent)

        return registry


def _builtin_agent_map() -> dict[str, Any]:
    """Lazy import to avoid circular deps. Maps agent_id to class."""
    from agents.loop_simplifier import LoopSimplifier
    from agents.pattern_optimizer import PatternOptimizer
    from agents.security_enforcer import SecurityEnforcer

    return {
        "pattern_optimizer": PatternOptimizer,
        "security_enforcer": SecurityEnforcer,
        "loop_simplifier": LoopSimplifier,
    }
