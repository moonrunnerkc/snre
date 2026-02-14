# Author: Bradley R. Kinnard
"""
Contract compliance check -- verifies critical imports and module structure.
Run as part of CI before tests to catch structural issues early.
"""

import os
import sys

# ensure project root is on path (for CI and standalone runs)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)


def check_contracts() -> None:
    """Verify all core modules are importable and expose expected symbols."""
    failures: list[str] = []

    checks = [
        ("snre.models.config", ["SNREConfig", "Config"]),
        ("snre.models.changes", ["Change", "AgentAnalysis", "ConsensusDecision"]),
        ("snre.models.session", ["RefactorSession"]),
        ("snre.models.enums", ["RefactorStatus", "ChangeType"]),
        ("snre.errors", ["SNREError", "AgentNotFoundError", "SessionNotFoundError"]),
        ("agents.base_agent", ["BaseAgent"]),
        ("agents.pattern_optimizer", ["PatternOptimizer"]),
        ("agents.security_enforcer", ["SecurityEnforcer"]),
        ("agents.loop_simplifier", ["LoopSimplifier"]),
        ("core.swarm_coordinator", ["SwarmCoordinator"]),
        ("core.consensus_engine", ["ConsensusEngine"]),
        ("core.change_tracker", ["ChangeTracker"]),
        ("core.evolution_recorder", ["EvolutionRecorder"]),
    ]

    for module_path, symbols in checks:
        try:
            mod = __import__(module_path, fromlist=symbols)
        except ImportError as exc:
            failures.append(f"FAIL: cannot import {module_path}: {exc}")
            continue

        for sym in symbols:
            if not hasattr(mod, sym):
                failures.append(f"FAIL: {module_path} missing symbol '{sym}'")

    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(1)

    print(
        f"OK: {sum(len(s) for _, s in checks)} symbols verified across {len(checks)} modules"
    )


if __name__ == "__main__":
    check_contracts()
