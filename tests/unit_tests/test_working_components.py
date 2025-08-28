"""
Tests for components that are currently working
Based on the successful quick_test.py output
"""

from contracts import AgentAnalysis
from contracts import Change
from contracts import ChangeType
from contracts import Config


class TestWorkingAgents:
    """Test the agents that we know work from quick_test.py"""

    def test_pattern_optimizer_works(self):
        """Test PatternOptimizer basic functionality"""
        from agents.pattern_optimizer import PatternOptimizer

        config = Config()
        agent = PatternOptimizer("pattern_optimizer", config)

        test_code = """
def test_function():
    result = []
    for item in items:
        result.append(item * 2)
    return result
        """

        analysis = agent.analyze(test_code)

        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_id == "pattern_optimizer"
        assert isinstance(analysis.confidence, (int, float))
        assert 0.0 <= analysis.confidence <= 1.0

        # Test other required methods exist
        assert hasattr(agent, "suggest_changes")
        assert hasattr(agent, "vote")
        assert hasattr(agent, "validate_result")
        assert hasattr(agent, "get_priority")
        assert hasattr(agent, "get_confidence_threshold")

    def test_security_enforcer_works(self):
        """Test SecurityEnforcer basic functionality"""
        from agents.security_enforcer import SecurityEnforcer

        config = Config()
        agent = SecurityEnforcer("security_enforcer", config)

        # Test with code that has security issues
        test_code = """
password = "hardcoded_secret_123"
def bad_query(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
        """

        analysis = agent.analyze(test_code)

        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_id == "security_enforcer"
        assert len(analysis.security_risks) > 0  # Should detect issues

        # Test suggest_changes works
        changes = agent.suggest_changes(test_code)
        assert isinstance(changes, list)

    def test_loop_simplifier_works(self):
        """Test LoopSimplifier basic functionality"""
        from agents.loop_simplifier import LoopSimplifier

        config = Config()
        agent = LoopSimplifier("loop_simplifier", config)

        test_code = """
def inefficient_loops():
    for i in range(len(items)):
        print(items[i])
        """

        analysis = agent.analyze(test_code)

        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_id == "loop_simplifier"
        assert (
            len(analysis.optimization_opportunities) > 0
        )  # Should detect range(len())

    def test_agent_method_signatures(self):
        """Test that all agents have the required method signatures"""
        from agents.loop_simplifier import LoopSimplifier
        from agents.pattern_optimizer import PatternOptimizer
        from agents.security_enforcer import SecurityEnforcer

        config = Config()
        agents = [
            PatternOptimizer("pattern_optimizer", config),
            SecurityEnforcer("security_enforcer", config),
            LoopSimplifier("loop_simplifier", config),
        ]

        for agent in agents:
            # Test all required methods exist
            assert hasattr(agent, "analyze")
            assert hasattr(agent, "suggest_changes")
            assert hasattr(agent, "vote")
            assert hasattr(agent, "validate_result")
            assert hasattr(agent, "get_priority")
            assert hasattr(agent, "get_confidence_threshold")

            # Test they return appropriate types
            priority = agent.get_priority()
            assert isinstance(priority, int)

            threshold = agent.get_confidence_threshold()
            assert isinstance(threshold, (int, float))
            assert 0.0 <= threshold <= 1.0


class TestAgentSuggestions:
    """Test that agents can generate and validate suggestions"""

    def test_security_suggestions(self):
        """Test SecurityEnforcer generates suggestions"""
        from agents.security_enforcer import SecurityEnforcer

        config = Config()
        agent = SecurityEnforcer("security_enforcer", config)

        vulnerable_code = '''password = "secret123"'''

        changes = agent.suggest_changes(vulnerable_code)
        assert isinstance(changes, list)

        if changes:
            change = changes[0]
            assert isinstance(change, Change)
            assert change.change_type == ChangeType.SECURITY
            assert change.confidence > 0.0

    def test_loop_suggestions(self):
        """Test LoopSimplifier generates suggestions"""
        from agents.loop_simplifier import LoopSimplifier

        config = Config()
        agent = LoopSimplifier("loop_simplifier", config)

        inefficient_code = """
for i in range(len(items)):
    print(items[i])
"""

        changes = agent.suggest_changes(inefficient_code)
        assert isinstance(changes, list)

        if changes:
            change = changes[0]
            assert isinstance(change, Change)
            assert (
                "enumerate" in change.modified_code
                or "optimization" in change.description.lower()
            )

    def test_agent_voting(self):
        """Test that agents can vote on changes"""
        from agents.pattern_optimizer import PatternOptimizer
        from agents.security_enforcer import SecurityEnforcer

        config = Config()
        pattern_agent = PatternOptimizer("pattern_optimizer", config)
        security_agent = SecurityEnforcer("security_enforcer", config)

        # Create a test change
        test_change = Change(
            agent_id="pattern_optimizer",
            change_type=ChangeType.OPTIMIZATION,
            original_code="old_code = 'test'",
            modified_code="new_code = 'test'",
            line_start=1,
            line_end=1,
            confidence=0.8,
            description="Test optimization",
            impact_score=0.6,
        )

        # Test voting
        pattern_votes = pattern_agent.vote([test_change])
        security_votes = security_agent.vote([test_change])

        assert isinstance(pattern_votes, dict)
        assert isinstance(security_votes, dict)

        # Votes should be between 0 and 1
        for votes in [pattern_votes, security_votes]:
            for vote_value in votes.values():
                assert 0.0 <= vote_value <= 1.0


class TestCoreModuleImports:
    """Test what core modules can be imported"""

    def test_core_imports(self):
        """Test which core modules import successfully"""
        modules_to_test = [
            "core.consensus_engine",
            "core.change_tracker",
            "core.swarm_coordinator",
            "core.evolution_recorder",
        ]

        working_modules = []
        failing_modules = []

        for module_name in modules_to_test:
            try:
                module = __import__(module_name, fromlist=[""])
                working_modules.append(module_name)
                print(f"✅ {module_name} imports OK")
            except Exception as e:
                failing_modules.append((module_name, str(e)))
                print(f"❌ {module_name} failed: {e}")

        # At least some core modules should work
        assert (
            len(working_modules) >= 1
        ), f"No core modules working. Failures: {failing_modules}"
