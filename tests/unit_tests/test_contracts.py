"""
Contract validation tests for SNRE
Auto-generated tests to ensure no drift from frozen contract
"""

from datetime import datetime
from uuid import uuid4

from agents.loop_simplifier import LoopSimplifier
from agents.pattern_optimizer import PatternOptimizer
from agents.security_enforcer import SecurityEnforcer
from contracts import *
from core.change_tracker import ChangeTracker
from core.consensus_engine import ConsensusEngine
from core.evolution_recorder import EvolutionRecorder
from core.swarm_coordinator import SwarmCoordinator
from interface.api import APIInterface
from interface.cli import CLIInterface
from interface.integration_hook import IntegrationHook


class TestContractCompliance:
    """Test that all contract classes and methods exist"""

    def test_config_contract(self):
        """Test Config class contract compliance"""
        config = Config()

        # Check required attributes
        assert hasattr(config, 'max_concurrent_agents')
        assert hasattr(config, 'consensus_threshold')
        assert hasattr(config, 'max_iterations')
        assert hasattr(config, 'timeout_seconds')
        assert hasattr(config, 'enable_evolution_log')
        assert hasattr(config, 'snapshot_frequency')
        assert hasattr(config, 'max_snapshots')
        assert hasattr(config, 'git_auto_commit')
        assert hasattr(config, 'backup_original')
        assert hasattr(config, 'create_branch')

        # Test kwargs functionality
        config_with_kwargs = Config(custom_param=True, another_param=42)
        assert hasattr(config_with_kwargs, 'custom_param')
        assert hasattr(config_with_kwargs, 'another_param')

    def test_agent_profile_contract(self):
        """Test AgentProfile dataclass contract"""
        profile = AgentProfile(
            name="Test Agent",
            priority=5,
            enabled=True,
            patterns=["test_pattern"],
            confidence_threshold=0.5,
            config={}
        )

        assert hasattr(profile, 'name')
        assert hasattr(profile, 'priority')
        assert hasattr(profile, 'enabled')
        assert hasattr(profile, 'patterns')
        assert hasattr(profile, 'confidence_threshold')
        assert hasattr(profile, 'config')

    def test_enum_contracts(self):
        """Test enum contracts"""
        # Test RefactorStatus
        assert hasattr(RefactorStatus, 'STARTED')
        assert hasattr(RefactorStatus, 'IN_PROGRESS')
        assert hasattr(RefactorStatus, 'COMPLETED')
        assert hasattr(RefactorStatus, 'FAILED')
        assert hasattr(RefactorStatus, 'CANCELLED')

        # Test ChangeType
        assert hasattr(ChangeType, 'OPTIMIZATION')
        assert hasattr(ChangeType, 'SECURITY')
        assert hasattr(ChangeType, 'READABILITY')
        assert hasattr(ChangeType, 'PERFORMANCE')
        assert hasattr(ChangeType, 'STRUCTURE')

    def test_data_structure_contracts(self):
        """Test data structure contracts"""
        # Test Change dataclass
        change = Change(
            agent_id="test",
            change_type=ChangeType.OPTIMIZATION,
            original_code="old",
            modified_code="new",
            line_start=0,
            line_end=1,
            confidence=0.8,
            description="test",
            impact_score=0.5
        )

        assert hasattr(change, 'agent_id')
        assert hasattr(change, 'change_type')
        assert hasattr(change, 'original_code')
        assert hasattr(change, 'modified_code')
        assert hasattr(change, 'line_start')
        assert hasattr(change, 'line_end')
        assert hasattr(change, 'confidence')
        assert hasattr(change, 'description')
        assert hasattr(change, 'impact_score')

        # Test RefactorSession
        session = RefactorSession(
            refactor_id=uuid4(),
            target_path="test.py",
            status=RefactorStatus.STARTED,
            progress=0,
            agent_set=["test"],
            original_code="test",
            refactored_code=None,
            evolution_history=[],
            consensus_log=[],
            metrics=None,
            started_at=datetime.now(),
            completed_at=None,
            error_message=None
        )

        assert hasattr(session, 'refactor_id')
        assert hasattr(session, 'target_path')
        assert hasattr(session, 'status')
        assert hasattr(session, 'progress')
        assert hasattr(session, 'agent_set')

    def test_agent_contracts(self):
        """Test agent class contracts"""
        config = Config()

        # Test PatternOptimizer
        optimizer = PatternOptimizer("test_optimizer", config)
        assert hasattr(optimizer, 'analyze')
        assert hasattr(optimizer, 'suggest_changes')
        assert hasattr(optimizer, 'vote')
        assert hasattr(optimizer, 'validate_result')
        assert hasattr(optimizer, 'get_priority')
        assert hasattr(optimizer, 'get_confidence_threshold')
        assert hasattr(optimizer, 'detect_patterns')

        # Test SecurityEnforcer
        enforcer = SecurityEnforcer("test_security", config)
        assert hasattr(enforcer, 'analyze')
        assert hasattr(enforcer, 'suggest_changes')
        assert hasattr(enforcer, 'vote')
        assert hasattr(enforcer, 'validate_result')
        assert hasattr(enforcer, 'scan_vulnerabilities')

        # Test LoopSimplifier
        simplifier = LoopSimplifier("test_loops", config)
        assert hasattr(simplifier, 'analyze')
        assert hasattr(simplifier, 'suggest_changes')
        assert hasattr(simplifier, 'vote')
        assert hasattr(simplifier, 'validate_result')
        assert hasattr(simplifier, 'optimize_loops')

    def test_core_contracts(self):
        """Test core component contracts"""
        config = Config()

        # Test SwarmCoordinator
        coordinator = SwarmCoordinator(config)
        assert hasattr(coordinator, 'register_agent')
        assert hasattr(coordinator, 'start_refactor')
        assert hasattr(coordinator, 'get_session_status')
        assert hasattr(coordinator, 'get_session_result')
        assert hasattr(coordinator, 'cancel_session')
        assert hasattr(coordinator, 'list_active_sessions')

        # Test ConsensusEngine
        consensus = ConsensusEngine(config)
        assert hasattr(consensus, 'collect_votes')
        assert hasattr(consensus, 'calculate_consensus')
        assert hasattr(consensus, 'apply_overrides')
        assert hasattr(consensus, 'validate_consensus')

        # Test ChangeTracker
        tracker = ChangeTracker(config)
        assert hasattr(tracker, 'create_diff')
        assert hasattr(tracker, 'calculate_metrics')
        assert hasattr(tracker, 'validate_syntax')
        assert hasattr(tracker, 'measure_complexity')

        # Test EvolutionRecorder
        recorder = EvolutionRecorder(config)
        assert hasattr(recorder, 'record_step')
        assert hasattr(recorder, 'create_snapshot')
        assert hasattr(recorder, 'get_evolution_history')
        assert hasattr(recorder, 'cleanup_old_snapshots')

    def test_interface_contracts(self):
        """Test interface contracts"""
        config = Config()
        coordinator = SwarmCoordinator(config)

        # Test CLIInterface
        cli = CLIInterface(coordinator, config)
        assert hasattr(cli, 'handle_start_command')
        assert hasattr(cli, 'handle_status_command')
        assert hasattr(cli, 'handle_result_command')
        assert hasattr(cli, 'handle_list_command')
        assert hasattr(cli, 'handle_cancel_command')
        assert hasattr(cli, 'handle_validate_command')

        # Test APIInterface
        api = APIInterface(coordinator, config)
        assert hasattr(api, 'start_refactor_endpoint')
        assert hasattr(api, 'get_status_endpoint')
        assert hasattr(api, 'get_result_endpoint')
        assert hasattr(api, 'list_sessions_endpoint')
        assert hasattr(api, 'cancel_session_endpoint')

        # Test IntegrationHook
        hook = IntegrationHook(coordinator, config)
        assert hasattr(hook, 'setup_git_hooks')
        assert hasattr(hook, 'validate_pre_commit')
        assert hasattr(hook, 'trigger_post_commit')
        assert hasattr(hook, 'setup_ide_integration')

    def test_exception_contracts(self):
        """Test exception class contracts"""
        # Test base exception
        error = SNREError("TEST_CODE", "Test message")
        assert hasattr(error, 'code')
        assert hasattr(error, 'message')
        assert hasattr(error, 'details')

        # Test specific exceptions
        assert issubclass(InvalidPathError, SNREError)
        assert issubclass(AgentNotFoundError, SNREError)
        assert issubclass(SessionNotFoundError, SNREError)
        assert issubclass(ConsensusFailedError, SNREError)
        assert issubclass(TimeoutError, SNREError)
        assert issubclass(PermissionDeniedError, SNREError)

    def test_main_application_contract(self):
        """Test main application contract - create directly since we can't import"""
        # Import here to avoid circular imports
        import os
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Test that we can create the application components directly
        config = Config()
        coordinator = SwarmCoordinator(config)
        consensus_engine = ConsensusEngine(config)
        change_tracker = ChangeTracker(config)
        evolution_recorder = EvolutionRecorder(config)
        cli_interface = CLIInterface(coordinator, config)
        api_interface = APIInterface(coordinator, config)
        integration_hook = IntegrationHook(coordinator, config)

        # Test that all components can be created
        assert config is not None
        assert coordinator is not None
        assert consensus_engine is not None
        assert change_tracker is not None
        assert evolution_recorder is not None
        assert cli_interface is not None
        assert api_interface is not None
        assert integration_hook is not None
