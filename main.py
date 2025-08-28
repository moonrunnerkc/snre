"""
SNRE Main Application Entry Point
"""

import os
import sys
from typing import Optional

import yaml

from agents.loop_simplifier import LoopSimplifier
from agents.pattern_optimizer import PatternOptimizer
from agents.security_enforcer import SecurityEnforcer
from contracts import Config
from core.change_tracker import ChangeTracker
from core.consensus_engine import ConsensusEngine
from core.evolution_recorder import EvolutionRecorder
from core.swarm_coordinator import SwarmCoordinator
from interface.api import APIInterface
from interface.cli import CLIInterface
from interface.integration_hook import IntegrationHook


class SNREApplication:
    """Main SNRE application orchestrator"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = Config()
        if config_path:
            self.load_config(config_path)

        # Initialize core components
        self.coordinator = SwarmCoordinator(self.config)
        self.consensus_engine = ConsensusEngine(self.config)
        self.change_tracker = ChangeTracker(self.config)
        self.evolution_recorder = EvolutionRecorder(self.config)

        # Initialize interfaces
        self.cli_interface = CLIInterface(self.coordinator, self.config)
        self.api_interface = APIInterface(self.coordinator, self.config)
        self.integration_hook = IntegrationHook(self.coordinator, self.config)

        # Initialize and register agents
        self._setup_agents()

    def initialize(self) -> None:
        """Initialize all system components"""
        print("Initializing SNRE...")

        # Create necessary directories
        os.makedirs("data/refactor_logs", exist_ok=True)
        os.makedirs("data/snapshots", exist_ok=True)

        # Load agent configurations
        self._load_agent_profiles()

        print(f"SNRE initialized with {len(self.coordinator.agents)} agents")

    def load_config(self, config_path: str) -> None:
        """Load configuration from file"""
        try:
            with open(config_path) as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    config_data = yaml.safe_load(f)
                else:
                    import json
                    config_data = json.load(f)

            # Update config with loaded values
            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {str(e)}")

    def start_cli(self, args: list[str] = None) -> None:
        """Start CLI interface with optional args"""
        self.cli_interface.run(args)

    def start_api_server(self, host: str = "localhost", port: int = 8000) -> None:
        """Start REST API server"""
        print(f"Starting SNRE API server on {host}:{port}")
        self.api_interface.run(host, port)

    def shutdown(self) -> None:
        """Clean shutdown of all components"""
        print("Shutting down SNRE...")

        # Clean up old snapshots
        self.evolution_recorder.cleanup_old_snapshots()

        print("SNRE shutdown complete")

    def _setup_agents(self) -> None:
        """Initialize and register default agents"""
        agents = [
            PatternOptimizer("pattern_optimizer", self.config),
            SecurityEnforcer("security_enforcer", self.config),
            LoopSimplifier("loop_simplifier", self.config)
        ]

        for agent in agents:
            self.coordinator.register_agent(agent)

    def _load_agent_profiles(self) -> None:
        """Load agent profiles from configuration"""
        profiles_path = "config/agent_profiles.yaml"

        if os.path.exists(profiles_path):
            try:
                with open(profiles_path) as f:
                    profiles = yaml.safe_load(f)

                # Update agent configurations based on profiles
                for agent_id, agent in self.coordinator.agents.items():
                    if agent_id in profiles.get('agents', {}):
                        profile = profiles['agents'][agent_id]
                        agent._priority = profile.get('priority', agent._priority)
                        agent._confidence_threshold = profile.get('confidence_threshold', agent._confidence_threshold)

            except Exception as e:
                print(f"Warning: Could not load agent profiles: {str(e)}")


def main():
    """Main entry point for CLI commands"""
    # Check if this is the old-style mode call (cli/api) or direct command
    if len(sys.argv) >= 2 and sys.argv[1] in ['cli', 'api']:
        # Old-style mode-based calling
        mode = sys.argv[1]

        # Initialize application
        app = SNREApplication()
        app.initialize()

        try:
            if mode == "cli":
                # Pass remaining args to CLI
                app.start_cli(sys.argv[2:])  # Skip 'main.py' and 'cli'
            elif mode == "api":
                host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
                port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
                app.start_api_server(host, port)

        except KeyboardInterrupt:
            print("\nShutdown requested...")
        finally:
            app.shutdown()

    else:
        # Direct command calling (new style) - pass all args to CLI
        app = SNREApplication()
        app.initialize()

        try:
            # Pass all args except the script name to CLI
            app.start_cli(sys.argv[1:])
        except KeyboardInterrupt:
            print("\nShutdown requested...")
        finally:
            app.shutdown()


if __name__ == "__main__":
    main()
