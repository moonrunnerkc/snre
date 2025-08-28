"""
Functional tests for SNRE components
"""

import os
import tempfile
from uuid import uuid4

import pytest

from agents.loop_simplifier import LoopSimplifier
from agents.pattern_optimizer import PatternOptimizer
from agents.security_enforcer import SecurityEnforcer
from contracts import *
from core.change_tracker import ChangeTracker
from core.consensus_engine import ConsensusEngine
from core.swarm_coordinator import SwarmCoordinator


class TestAgentFunctionality:
    """Test agent functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.config = Config()

    def test_pattern_optimizer_analysis(self):
        """Test pattern optimizer analysis"""
        optimizer = PatternOptimizer("test_optimizer", self.config)

        test_code = """
result = []
for item in items:
    result.append(item * 2)
"""

        analysis = optimizer.analyze(test_code)
        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_id == "test_optimizer"
        assert len(analysis.optimization_opportunities) > 0

    def test_security_enforcer_scan(self):
        """Test security enforcer vulnerability scanning"""
        enforcer = SecurityEnforcer("test_security", self.config)

        vulnerable_code = """
password = "hardcoded_password"
cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
"""

        vulnerabilities = enforcer.scan_vulnerabilities(vulnerable_code)
        assert len(vulnerabilities) > 0
        assert any("hardcoded" in vuln for vuln in vulnerabilities)

    def test_loop_simplifier_optimization(self):
        """Test loop simplifier optimization"""
        simplifier = LoopSimplifier("test_loops", self.config)

        inefficient_code = """
for i in range(len(items)):
    process(items[i])
"""

        changes = simplifier.optimize_loops(inefficient_code)
        assert len(changes) > 0
        assert any("enumerate" in change.description for change in changes)


class TestCoreComponents:
    """Test core component functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.config = Config()
        self.coordinator = SwarmCoordinator(self.config)

        # Register test agents
        self.coordinator.register_agent(PatternOptimizer("pattern_optimizer", self.config))
        self.coordinator.register_agent(SecurityEnforcer("security_enforcer", self.config))

    def test_consensus_engine(self):
        """Test consensus calculation"""
        engine = ConsensusEngine(self.config)

        # Mock votes from agents
        votes = {
            "agent1": {"change_1": 0.8, "change_2": 0.6},
            "agent2": {"change_1": 0.7, "change_2": 0.9}
        }

        decision = engine.calculate_consensus(votes)
        assert isinstance(decision, ConsensusDecision)
        assert decision.confidence > 0.0

    def test_change_tracker_diff(self):
        """Test change tracking and diff generation"""
        tracker = ChangeTracker(self.config)

        original = "def old_function():\n    pass"
        modified = "def new_function():\n    return True"

        diff = tracker.create_diff(original, modified)
        assert "old_function" in diff
        assert "new_function" in diff

        metrics = tracker.calculate_metrics(original, modified)
        assert isinstance(metrics, RefactorMetrics)
        assert metrics.lines_changed >= 0

    def test_swarm_coordinator_agent_registration(self):
        """Test agent registration"""
        assert len(self.coordinator.agents) == 2
        assert "pattern_optimizer" in self.coordinator.agents
        assert "security_enforcer" in self.coordinator.agents

    def test_file_refactoring_flow(self):
        """Test complete refactoring flow with temp file"""
        # Create temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
password = "secret123"
result = []
for i in range(len(items)):
    result.append(items[i] * 2)
""")
            temp_path = f.name

        try:
            # Start refactoring
            session_id = self.coordinator.start_refactor(
                temp_path,
                ["security_enforcer", "pattern_optimizer"]
            )

            # Check session was created
            assert session_id in self.coordinator.active_sessions

            # Get status
            status = self.coordinator.get_session_status(session_id)
            assert status["status"] in ["started", "in_progress", "completed"]

            # Get results
            session = self.coordinator.get_session_result(session_id)
            assert isinstance(session, RefactorSession)
            assert session.refactor_id == session_id

        finally:
            # Clean up temp file
            os.unlink(temp_path)


class TestErrorHandling:
    """Test error handling contracts"""

    def test_snre_errors(self):
        """Test SNRE error classes"""
        # Test base error
        base_error = SNREError("TEST", "Test message", {"detail": "test"})
        assert base_error.code == "TEST"
        assert base_error.message == "Test message"
        assert base_error.details["detail"] == "test"

        # Test specific errors
        invalid_path = InvalidPathError("/nonexistent/path")
        assert invalid_path.code == "INVALID_PATH"

        agent_not_found = AgentNotFoundError("missing_agent")
        assert agent_not_found.code == "AGENT_NOT_FOUND"

        session_not_found = SessionNotFoundError("missing_session")
        assert session_not_found.code == "SESSION_NOT_FOUND"

    def test_coordinator_error_handling(self):
        """Test coordinator error handling"""
        coordinator = SwarmCoordinator(Config())

        # Test agent not found error
        with pytest.raises(AgentNotFoundError):
            coordinator.start_refactor("/tmp/test.py", ["nonexistent_agent"])

        # Test session not found error
        with pytest.raises(SessionNotFoundError):
            fake_id = uuid4()
            coordinator.get_session_status(fake_id)


if __name__ == "__main__":
    pytest.main([__file__])
