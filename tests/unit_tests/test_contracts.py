# Author: Bradley R. Kinnard
"""
Contract compliance tests for SNRE.
Behavioral assertions only -- no hasattr, no try/except ImportError.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from agents.base_agent import BaseAgent
from agents.loop_simplifier import LoopSimplifier
from agents.pattern_optimizer import PatternOptimizer
from agents.security_enforcer import SecurityEnforcer
from snre.errors import AgentNotFoundError
from snre.models.profiles import AgentProfile
from snre.models.changes import Change
from snre.models.enums import ChangeType
from snre.models.config import Config
from snre.errors import ConsensusFailedError
from snre.errors import InvalidPathError
from snre.errors import PermissionDeniedError
from snre.models.session import RefactorSession
from snre.models.enums import RefactorStatus
from snre.errors import SessionNotFoundError
from snre.errors import SNREError
from snre.errors import TimeoutError
from core.change_tracker import ChangeTracker
from core.consensus_engine import ConsensusEngine
from core.evolution_recorder import EvolutionRecorder
from core.swarm_coordinator import SwarmCoordinator
from interface.api import APIInterface
from interface.cli import CLIInterface
from interface.integration_hook import IntegrationHook


class TestConfigContract:
    """Config must validate fields and reject garbage"""

    def test_defaults_applied(self):
        config = Config()
        assert config.max_concurrent_agents == 5
        assert config.consensus_threshold == 0.6
        assert config.max_iterations == 10
        assert config.timeout_seconds == 300
        assert config.enable_evolution_log is True
        assert config.snapshot_frequency == 5

    def test_explicit_values(self):
        config = Config(consensus_threshold=0.9, max_iterations=20)
        assert config.consensus_threshold == 0.9
        assert config.max_iterations == 20

    def test_rejects_invalid_threshold(self):
        with pytest.raises(ValueError, match="consensus_threshold"):
            Config(consensus_threshold=1.5)
        with pytest.raises(ValueError, match="consensus_threshold"):
            Config(consensus_threshold=-0.1)

    def test_rejects_invalid_agents_count(self):
        with pytest.raises(ValueError, match="max_concurrent_agents"):
            Config(max_concurrent_agents=0)

    def test_rejects_invalid_iterations(self):
        with pytest.raises(ValueError, match="max_iterations"):
            Config(max_iterations=0)

    def test_rejects_low_timeout(self):
        with pytest.raises(ValueError, match="timeout_seconds"):
            Config(timeout_seconds=5)

    def test_rejects_unknown_kwargs(self):
        """dataclass __init__ must reject unknown fields"""
        with pytest.raises(TypeError):
            Config(made_up_field=42)


class TestAgentProfileContract:
    """AgentProfile dataclass shape"""

    def test_creation(self):
        profile = AgentProfile(
            name="Test Agent",
            priority=5,
            enabled=True,
            patterns=["test_pattern"],
            confidence_threshold=0.5,
            config={},
        )
        assert profile.name == "Test Agent"
        assert profile.priority == 5
        assert profile.enabled is True
        assert profile.patterns == ["test_pattern"]
        assert profile.confidence_threshold == 0.5


class TestEnumContracts:
    """Enums must have the documented members"""

    def test_refactor_status_members(self):
        assert RefactorStatus.STARTED.value == "started"
        assert RefactorStatus.IN_PROGRESS.value == "in_progress"
        assert RefactorStatus.COMPLETED.value == "completed"
        assert RefactorStatus.FAILED.value == "failed"
        assert RefactorStatus.CANCELLED.value == "cancelled"

    def test_change_type_members(self):
        assert ChangeType.OPTIMIZATION.value == "optimization"
        assert ChangeType.SECURITY.value == "security"
        assert ChangeType.READABILITY.value == "readability"
        assert ChangeType.PERFORMANCE.value == "performance"
        assert ChangeType.STRUCTURE.value == "structure"


class TestChangeDataclass:
    """Change must hold all required fields"""

    def test_round_trip(self):
        change = Change(
            agent_id="test",
            change_type=ChangeType.OPTIMIZATION,
            original_code="old",
            modified_code="new",
            line_start=0,
            line_end=1,
            confidence=0.8,
            description="test change",
            impact_score=0.5,
        )
        assert change.agent_id == "test"
        assert change.change_type == ChangeType.OPTIMIZATION
        assert change.confidence == 0.8
        assert change.line_start == 0
        assert change.line_end == 1


class TestRefactorSession:
    """RefactorSession must serialize and deserialize cleanly"""

    def test_creation_and_to_dict(self):
        sid = uuid4()
        session = RefactorSession(
            refactor_id=sid,
            target_path="test.py",
            status=RefactorStatus.STARTED,
            progress=0,
            agent_set=["pattern_optimizer"],
            original_code="x = 1",
            refactored_code=None,
            evolution_history=[],
            consensus_log=[],
            metrics=None,
            started_at=datetime.now(),
            completed_at=None,
            error_message=None,
        )
        data = session.to_dict()
        assert data["refactor_id"] == str(sid)
        assert data["target_path"] == "test.py"
        assert data["status"] == "started"

    def test_round_trip_serialization(self):
        sid = uuid4()
        now = datetime.now()
        session = RefactorSession(
            refactor_id=sid,
            target_path="code.py",
            status=RefactorStatus.IN_PROGRESS,
            progress=50,
            agent_set=["security_enforcer"],
            original_code="pass",
            refactored_code=None,
            evolution_history=[],
            consensus_log=[],
            metrics=None,
            started_at=now,
            completed_at=None,
            error_message=None,
        )
        data = session.to_dict()
        restored = RefactorSession.from_dict(data)
        assert str(restored.refactor_id) == str(sid)
        assert restored.target_path == "code.py"
        assert restored.status == RefactorStatus.IN_PROGRESS


class TestAgentInheritance:
    """All agents must be instances of BaseAgent and produce correct outputs"""

    def test_pattern_optimizer_is_base_agent(self):
        config = Config()
        agent = PatternOptimizer("po_test", config)
        assert isinstance(agent, BaseAgent)

    def test_security_enforcer_is_base_agent(self):
        config = Config()
        agent = SecurityEnforcer("se_test", config)
        assert isinstance(agent, BaseAgent)

    def test_loop_simplifier_is_base_agent(self):
        config = Config()
        agent = LoopSimplifier("ls_test", config)
        assert isinstance(agent, BaseAgent)

    def test_pattern_optimizer_analyze(self):
        config = Config()
        agent = PatternOptimizer("po_test", config)
        result = agent.analyze("x = 1")
        assert result.agent_id == "po_test"
        assert isinstance(result.issues_found, int)
        assert isinstance(result.complexity_score, (int, float))

    def test_security_enforcer_detects_vulns(self):
        config = Config()
        agent = SecurityEnforcer("se_test", config)
        result = agent.analyze('password = "hunter2_longpass"')
        assert result.agent_id == "se_test"
        assert len(result.security_risks) > 0

    def test_loop_simplifier_detects_issues(self):
        config = Config()
        agent = LoopSimplifier("ls_test", config)
        code = "for i in range(len(items)):\n    print(items[i])"
        result = agent.analyze(code)
        assert result.agent_id == "ls_test"
        assert result.issues_found > 0

    def test_all_agents_vote(self):
        config = Config()
        change = Change(
            agent_id="test",
            change_type=ChangeType.OPTIMIZATION,
            original_code="a",
            modified_code="b",
            line_start=0,
            line_end=0,
            confidence=0.8,
            description="test",
            impact_score=0.5,
        )
        for cls in [PatternOptimizer, SecurityEnforcer, LoopSimplifier]:
            agent = cls("voter", config)
            votes = agent.vote([change])
            assert isinstance(votes, dict)
            for v in votes.values():
                assert 0.0 <= v <= 1.0

    def test_all_agents_validate(self):
        config = Config()
        for cls in [PatternOptimizer, SecurityEnforcer, LoopSimplifier]:
            agent = cls("val", config)
            result = agent.validate_result("x = 1", "x = 2")
            assert isinstance(result, bool)

    def test_all_agents_priority_and_threshold(self):
        config = Config()
        for cls in [PatternOptimizer, SecurityEnforcer, LoopSimplifier]:
            agent = cls("pri", config)
            assert isinstance(agent.get_priority(), int)
            threshold = agent.get_confidence_threshold()
            assert isinstance(threshold, float)
            assert 0.0 <= threshold <= 1.0


class TestCoreContracts:
    """Core components must instantiate and expose working methods"""

    def test_swarm_coordinator_registers_agent(self):
        config = Config()
        coordinator = SwarmCoordinator(config)
        agent = PatternOptimizer("po", config)
        coordinator.register_agent(agent)
        assert "po" in coordinator.agents

    def test_consensus_engine_collects_votes(self):
        config = Config()
        engine = ConsensusEngine(config)
        agents = {"po": PatternOptimizer("po", config)}
        changes = [
            Change(
                agent_id="po",
                change_type=ChangeType.OPTIMIZATION,
                original_code="a",
                modified_code="b",
                line_start=0,
                line_end=0,
                confidence=0.8,
                description="test",
                impact_score=0.5,
            )
        ]
        votes = engine.collect_votes(agents, changes)
        assert isinstance(votes, dict)

    def test_change_tracker_creates_diff(self):
        config = Config()
        tracker = ChangeTracker(config)
        diff = tracker.create_diff("old code", "new code")
        assert isinstance(diff, str)
        assert len(diff) > 0

    def test_evolution_recorder_paths(self):
        config = Config()
        recorder = EvolutionRecorder(config)
        assert recorder.snapshots_dir == "data/snapshots"
        assert recorder.logs_dir == "data/refactor_logs"


class TestInterfaceContracts:
    """Interfaces must instantiate without errors"""

    def test_cli_interface(self):
        config = Config()
        coordinator = SwarmCoordinator(config)
        cli = CLIInterface(coordinator, config)
        assert cli is not None

    def test_api_interface(self):
        config = Config()
        coordinator = SwarmCoordinator(config)
        api = APIInterface(coordinator, config)
        assert api is not None

    def test_integration_hook(self):
        config = Config()
        coordinator = SwarmCoordinator(config)
        hook = IntegrationHook(coordinator, config)
        assert hook is not None


class TestExceptionHierarchy:
    """Error classes must subclass SNREError and carry context"""

    def test_base_error(self):
        err = SNREError("TEST_001", "something broke")
        assert err.code == "TEST_001"
        assert err.message == "something broke"

    def test_subclass_chain(self):
        assert issubclass(InvalidPathError, SNREError)
        assert issubclass(AgentNotFoundError, SNREError)
        assert issubclass(SessionNotFoundError, SNREError)
        assert issubclass(ConsensusFailedError, SNREError)
        assert issubclass(TimeoutError, SNREError)
        assert issubclass(PermissionDeniedError, SNREError)

    def test_exceptions_are_raisable(self):
        with pytest.raises(SNREError):
            raise InvalidPathError("bad/path")
        with pytest.raises(SNREError):
            raise AgentNotFoundError("ghost_agent")
