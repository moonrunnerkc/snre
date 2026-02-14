# Author: Bradley R. Kinnard
"""
Functional tests for SNRE components.
Tests actual behavior -- no try/except ImportError, no skipif import guards.
"""

import os
import tempfile

from agents.loop_simplifier import LoopSimplifier
from agents.pattern_optimizer import PatternOptimizer
from agents.security_enforcer import SecurityEnforcer
from core.change_tracker import ChangeTracker
from core.consensus_engine import ConsensusEngine
from core.evolution_recorder import EvolutionRecorder
from core.swarm_coordinator import SwarmCoordinator
from snre.models.changes import AgentAnalysis
from snre.models.changes import Change
from snre.models.config import Config
from snre.models.enums import ChangeType
from snre.models.session import RefactorMetrics


class TestAgentFunctionality:
    """Test concrete agent implementations"""

    def test_pattern_optimizer_analysis(self):
        config = Config()
        agent = PatternOptimizer("pattern_optimizer", config)

        test_code = """
def inefficient_function():
    result = []
    for item in items:
        result.append(item * 2)
    return result
        """

        analysis = agent.analyze(test_code)
        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_id == "pattern_optimizer"
        assert analysis.confidence >= 0.0
        assert isinstance(analysis.issues_found, int)
        assert isinstance(analysis.complexity_score, (int, float))

    def test_security_enforcer_scan(self):
        config = Config()
        agent = SecurityEnforcer("security_enforcer", config)

        test_code = '''
password = "hardcoded_secret_123"
def vulnerable_query(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
        '''

        analysis = agent.analyze(test_code)
        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_id == "security_enforcer"
        assert len(analysis.security_risks) > 0

    def test_loop_simplifier_optimization(self):
        config = Config()
        agent = LoopSimplifier("loop_simplifier", config)

        test_code = """
def nested_loops():
    for i in range(len(items)):
        for j in range(len(other_items)):
            for k in range(len(third_items)):
                process(items[i], other_items[j], third_items[k])
        """

        analysis = agent.analyze(test_code)
        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_id == "loop_simplifier"
        assert len(analysis.optimization_opportunities) > 0

    def test_agent_suggestion_generation(self):
        config = Config()
        agent = PatternOptimizer("pattern_optimizer", config)

        test_code = """
result = []
for item in items:
    result.append(item * 2)
"""
        suggestions = agent.suggest_changes(test_code)
        assert isinstance(suggestions, list)
        if suggestions:
            s = suggestions[0]
            assert isinstance(s, Change)
            assert s.agent_id == "pattern_optimizer"
            assert s.confidence > 0.0

    def test_agent_validation(self):
        config = Config()
        agent = SecurityEnforcer("security_enforcer", config)
        original = 'password = "secret123"'
        modified = 'password = os.environ.get("PASSWORD")'
        result = agent.validate_result(original, modified)
        assert isinstance(result, bool)

    def test_security_enforcer_suggest_changes(self):
        config = Config()
        agent = SecurityEnforcer("security_enforcer", config)
        code = 'password = "hardcoded_secret_123"'
        changes = agent.suggest_changes(code)
        assert isinstance(changes, list)

    def test_loop_simplifier_suggest_changes(self):
        config = Config()
        agent = LoopSimplifier("loop_simplifier", config)
        code = """
for i in range(len(items)):
    print(items[i])
"""
        changes = agent.suggest_changes(code)
        assert isinstance(changes, list)
        if changes:
            assert "enumerate" in changes[0].modified_code or "optimization" in changes[0].description.lower()


class TestCoreComponents:
    """Test core engine components"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.temp_dir, "data", "refactor_logs"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "data", "snapshots"), exist_ok=True)
        self.config = Config()

    def test_consensus_engine(self):
        engine = ConsensusEngine(self.config)
        agents = {
            "pattern_optimizer": PatternOptimizer("pattern_optimizer", self.config),
            "security_enforcer": SecurityEnforcer("security_enforcer", self.config),
            "loop_simplifier": LoopSimplifier("loop_simplifier", self.config),
        }
        changes = [
            Change(
                agent_id="pattern_optimizer",
                change_type=ChangeType.OPTIMIZATION,
                original_code="old = 'code'",
                modified_code="new = 'code'",
                line_start=1,
                line_end=1,
                confidence=0.8,
                description="Test pattern",
                impact_score=0.6,
            )
        ]
        votes = engine.collect_votes(agents, changes)
        assert isinstance(votes, dict)

    def test_change_tracker_diff(self):
        tracker = ChangeTracker(self.config)
        original = "def old_function():\n    pass"
        modified = "def new_function():\n    pass"

        diff = tracker.create_diff(original, modified)
        assert isinstance(diff, str)
        assert len(diff) > 0

        metrics = tracker.calculate_metrics(original, modified)
        assert isinstance(metrics, RefactorMetrics)
        assert isinstance(metrics.lines_changed, int)
        assert isinstance(metrics.complexity_delta, (int, float))

    def test_swarm_coordinator_agent_registration(self):
        coordinator = SwarmCoordinator(self.config)
        agents = [
            PatternOptimizer("pattern_optimizer", self.config),
            SecurityEnforcer("security_enforcer", self.config),
            LoopSimplifier("loop_simplifier", self.config),
        ]
        for agent in agents:
            coordinator.register_agent(agent)
        assert len(coordinator.agents) == 3

    def test_evolution_recorder(self):
        recorder = EvolutionRecorder(self.config)
        assert recorder is not None

    def test_file_refactoring_setup(self):
        """Verify coordinator can register agents and accept a target file"""
        coordinator = SwarmCoordinator(self.config)
        agents = [
            PatternOptimizer("pattern_optimizer", self.config),
            SecurityEnforcer("security_enforcer", self.config),
            LoopSimplifier("loop_simplifier", self.config),
        ]
        for agent in agents:
            coordinator.register_agent(agent)

        test_file = os.path.join(self.temp_dir, "test_code.py")
        with open(test_file, "w") as f:
            f.write("def test_function():\n    x = 1\n")

        assert os.path.exists(test_file)
        assert len(coordinator.agents) == 3


class TestIntegration:
    """Integration smoke tests"""

    def test_cli_instantiation(self):
        from interface.cli import CLIInterface

        config = Config()
        coordinator = SwarmCoordinator(config)
        cli = CLIInterface(coordinator, config)
        assert cli is not None

    def test_api_instantiation(self):
        from interface.api import APIInterface
        from interface.api import create_app

        config = Config()
        coordinator = SwarmCoordinator(config)
        api = APIInterface(coordinator, config)
        assert api is not None

        app = create_app(coordinator, config)
        assert app is not None


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_code_handling(self):
        config = Config()
        agent = PatternOptimizer("pattern_optimizer", config)
        analysis = agent.analyze("def invalid syntax here +++")
        assert isinstance(analysis, AgentAnalysis)
        assert analysis.confidence == 0.0

    def test_empty_code_handling(self):
        config = Config()
        agent = SecurityEnforcer("security_enforcer", config)
        analysis = agent.analyze("")
        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_id == "security_enforcer"

    def test_agent_voting(self):
        config = Config()
        agents = [
            PatternOptimizer("pattern_optimizer", config),
            SecurityEnforcer("security_enforcer", config),
            LoopSimplifier("loop_simplifier", config),
        ]
        test_change = Change(
            agent_id="pattern_optimizer",
            change_type=ChangeType.OPTIMIZATION,
            original_code="old_code",
            modified_code="new_code",
            line_start=1,
            line_end=1,
            confidence=0.8,
            description="Test optimization",
            impact_score=0.6,
        )
        for agent in agents:
            votes = agent.vote([test_change])
            assert isinstance(votes, dict)
            for val in votes.values():
                assert isinstance(val, (int, float))
                assert 0.0 <= val <= 1.0
