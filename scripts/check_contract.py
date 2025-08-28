#!/usr/bin/env python3
"""
Contract-Cop Linter for SNRE
Ensures implementation matches frozen contracts
"""

import importlib.util
import inspect
import os
import sys


def load_contracts():
    """Load contracts module"""
    spec = importlib.util.spec_from_file_location("contracts", "contracts.py")
    contracts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contracts)
    return contracts


def get_contract_classes(contracts_module) -> dict[str, type]:
    """Extract all classes from contracts module"""
    classes = {}
    for name, obj in inspect.getmembers(contracts_module):
        if inspect.isclass(obj) and obj.__module__ == contracts_module.__name__:
            classes[name] = obj
    return classes


def get_contract_methods(class_obj: type) -> set[str]:
    """Get all methods defined in a contract class"""
    methods = set()
    for name, method in inspect.getmembers(class_obj):
        if inspect.isfunction(method) or inspect.ismethod(method):
            methods.add(name)
        elif hasattr(method, '__func__'):  # Handle abstractmethod
            methods.add(name)
    return methods


def check_implementation_exists(class_name: str, file_paths: list[str]) -> bool:
    """Check if class is implemented in any of the file paths"""
    for file_path in file_paths:
        if not os.path.exists(file_path):
            continue

        try:
            with open(file_path) as f:
                content = f.read()
                if f"class {class_name}" in content:
                    return True
        except Exception:
            continue

    return False


def check_method_exists(class_name: str, method_name: str, file_paths: list[str]) -> bool:
    """Check if method is implemented in class"""
    for file_path in file_paths:
        if not os.path.exists(file_path):
            continue

        try:
            with open(file_path) as f:
                content = f.read()

            if f"class {class_name}" in content:
                # Look for the method definition anywhere in the file after class declaration
                lines = content.split('\n')
                in_class = False
                class_indent = 0

                for line in lines:
                    if f"class {class_name}" in line:
                        in_class = True
                        class_indent = len(line) - len(line.lstrip())
                        continue

                    if in_class:
                        # Check if we've left the class (lower indentation with content)
                        if line.strip() and (len(line) - len(line.lstrip())) <= class_indent:
                            if not line.strip().startswith('#') and not line.strip().startswith('"""'):
                                in_class = False
                                continue

                        # Look for method definition
                        if f"def {method_name}" in line:
                            return True

        except Exception:
            continue

    return False


def main():
    """Main contract validation function"""
    if not os.path.exists("contracts.py"):
        print("ERROR: contracts.py not found")
        sys.exit(1)

    # Load contracts
    contracts_module = load_contracts()
    contract_classes = get_contract_classes(contracts_module)

    print(f"Checking {len(contract_classes)} contract classes...")

    # File path mapping for implementations
    implementation_files = {
        'BaseAgent': ['agents/base_agent.py'],
        'PatternOptimizer': ['agents/pattern_optimizer.py'],
        'SecurityEnforcer': ['agents/security_enforcer.py'],
        'LoopSimplifier': ['agents/loop_simplifier.py'],
        'SwarmCoordinator': ['core/swarm_coordinator.py'],
        'ConsensusEngine': ['core/consensus_engine.py'],
        'ChangeTracker': ['core/change_tracker.py'],
        'EvolutionRecorder': ['core/evolution_recorder.py'],
        'CLIInterface': ['interface/cli.py'],
        'APIInterface': ['interface/api.py'],
        'IntegrationHook': ['interface/integration_hook.py'],
        'SNREApplication': ['main.py']
    }

    errors = []

    # Check each contract class
    for class_name, class_obj in contract_classes.items():
        if class_name in implementation_files:
            file_paths = implementation_files[class_name]

            # Check if class exists
            if not check_implementation_exists(class_name, file_paths):
                errors.append(f"Missing implementation: {class_name}")
                continue

            # Check methods exist
            contract_methods = get_contract_methods(class_obj)
            for method_name in contract_methods:
                if not method_name.startswith('_'):  # Skip private methods
                    if not check_method_exists(class_name, method_name, file_paths):
                        errors.append(f"Missing method: {class_name}.{method_name}")

    # Check required config parameters
    config_class = getattr(contracts_module, 'Config', None)
    if config_class:
        required_config_attrs = [
            'max_concurrent_agents', 'consensus_threshold', 'max_iterations',
            'timeout_seconds', 'enable_evolution_log', 'snapshot_frequency',
            'max_snapshots', 'git_auto_commit', 'backup_original', 'create_branch'
        ]

        for attr in required_config_attrs:
            if not hasattr(config_class(), attr):
                errors.append(f"Missing Config attribute: {attr}")

    # Check enum values
    refactor_status = getattr(contracts_module, 'RefactorStatus', None)
    if refactor_status:
        required_statuses = ['STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED']
        for status in required_statuses:
            if not hasattr(refactor_status, status):
                errors.append(f"Missing RefactorStatus: {status}")

    change_type = getattr(contracts_module, 'ChangeType', None)
    if change_type:
        required_types = ['OPTIMIZATION', 'SECURITY', 'READABILITY', 'PERFORMANCE', 'STRUCTURE']
        for change_t in required_types:
            if not hasattr(change_type, change_t):
                errors.append(f"Missing ChangeType: {change_t}")

    # Report results
    if errors:
        print(f"\n❌ CONTRACT VIOLATIONS DETECTED ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
        print("\nContract validation FAILED")
        sys.exit(1)
    else:
        print("✅ All contracts validated successfully")
        print("Contract compliance: PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
