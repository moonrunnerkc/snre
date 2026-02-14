# Author: Bradley R. Kinnard
"""
Lightweight dependency injection container.
No framework -- just explicit construction and wiring.
Tests create their own Container with mock implementations.
"""

from typing import Optional
from typing import Union

from core.change_tracker import ChangeTracker
from core.consensus_engine import ConsensusEngine
from core.evolution_recorder import EvolutionRecorder
from core.swarm_coordinator import SwarmCoordinator
from snre.adapters.repository import FileSessionRepository
from snre.adapters.repository import SQLiteSessionRepository
from snre.agents.registry import AgentRegistry
from snre.models.config import SNREConfig


def _build_repository(
    config: SNREConfig,
) -> Union[FileSessionRepository, SQLiteSessionRepository]:
    """Pick storage backend from config."""
    if config.storage_backend == "sqlite":
        return SQLiteSessionRepository(db_path="data/snre.db")
    return FileSessionRepository(config.sessions_dir)


class Container:
    """Wires all dependencies explicitly. One per application lifetime."""

    def __init__(
        self,
        config: Optional[SNREConfig] = None,
        profiles_path: str = "config/agent_profiles.yaml",
    ) -> None:
        self.config = config or SNREConfig()
        self.repository = _build_repository(self.config)
        self.registry = AgentRegistry.from_profiles(profiles_path, self.config)
        self.consensus = ConsensusEngine(self.config)
        self.tracker = ChangeTracker(self.config)
        self.recorder = EvolutionRecorder(self.config)
        self.coordinator = SwarmCoordinator(self.config)

        # wire agents into coordinator
        for _id, agent in self.registry.all().items():
            self.coordinator.register_agent(agent)
