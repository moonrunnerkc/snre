#!/usr/bin/env python3
"""
SNRE CLI entry point - Direct CLI access without mode prefix
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """CLI entry point for SNRE"""
    # Import here to avoid circular imports
    from agents.loop_simplifier import LoopSimplifier
    from agents.pattern_optimizer import PatternOptimizer
    from agents.security_enforcer import SecurityEnforcer
    from contracts import Config
    from core.swarm_coordinator import SwarmCoordinator
    from interface.cli import CLIInterface

    # Initialize system components directly
    config = Config()
    coordinator = SwarmCoordinator(config)

    # Register agents
    coordinator.register_agent(PatternOptimizer("pattern_optimizer", config))
    coordinator.register_agent(SecurityEnforcer("security_enforcer", config))
    coordinator.register_agent(LoopSimplifier("loop_simplifier", config))

    # Create necessary directories
    os.makedirs("data/refactor_logs", exist_ok=True)
    os.makedirs("data/snapshots", exist_ok=True)

    print(f"SNRE initialized with {len(coordinator.agents)} agents")

    # Create CLI interface and run
    cli = CLIInterface(coordinator, config)

    try:
        cli.run()  # This will parse sys.argv[1:] automatically
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except SystemExit:
        pass  # Allow normal exits
    finally:
        # Clean shutdown
        for session_id in list(coordinator.active_sessions.keys()):
            coordinator.cancel_session(session_id)
        print("SNRE shutdown complete")


if __name__ == "__main__":
    main()
