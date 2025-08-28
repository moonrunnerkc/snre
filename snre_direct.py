#!/usr/bin/env python3
"""
SNRE Direct CLI Entry Point
"""

import argparse
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_parser():
    """Create argument parser for SNRE CLI"""
    parser = argparse.ArgumentParser(description="SNRE - Swarm Neural Refactoring Engine")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start refactoring session')
    start_parser.add_argument('--path', required=True, help='Target code path')
    start_parser.add_argument('--agents', help='Comma-separated list of agents')
    start_parser.add_argument('--config', help='Custom configuration file')
    start_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    # Status command
    status_parser = subparsers.add_parser('status', help='Get session status')
    status_parser.add_argument('refactor_id', help='Refactor session ID')

    # Result command
    result_parser = subparsers.add_parser('result', help='Get session results')
    result_parser.add_argument('refactor_id', help='Refactor session ID')
    result_parser.add_argument('--output', help='Output file for results')

    # Show command
    show_parser = subparsers.add_parser('show', help='Display refactored code')
    show_parser.add_argument('refactor_id', help='Refactor session ID')
    show_parser.add_argument('--diff', action='store_true', help='Show differences between original and refactored code')
    show_parser.add_argument('--line-numbers', action='store_true', help='Show line numbers')

    # Apply command
    apply_parser = subparsers.add_parser('apply', help='Apply refactored code to original file')
    apply_parser.add_argument('refactor_id', help='Refactor session ID')
    apply_parser.add_argument('--no-backup', action='store_true', help='Do not create backup of original file')
    apply_parser.add_argument('--force', action='store_true', help='Apply changes even if file was modified')

    # List command
    subparsers.add_parser('list', help='List active sessions')

    # Cancel command
    cancel_parser = subparsers.add_parser('cancel', help='Cancel session')
    cancel_parser.add_argument('refactor_id', help='Refactor session ID')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate code')
    validate_parser.add_argument('--path', required=True, help='Target code path')

    return parser


def initialize_snre():
    """Initialize SNRE system components"""
    from agents.loop_simplifier import LoopSimplifier
    from agents.pattern_optimizer import PatternOptimizer
    from agents.security_enforcer import SecurityEnforcer
    from contracts import Config
    from core.swarm_coordinator import SwarmCoordinator

    print("Initializing SNRE...")

    # Create directories
    os.makedirs("data/refactor_logs", exist_ok=True)
    os.makedirs("data/snapshots", exist_ok=True)

    # Initialize components
    config = Config()
    coordinator = SwarmCoordinator(config)

    # Register agents
    coordinator.register_agent(PatternOptimizer("pattern_optimizer", config))
    coordinator.register_agent(SecurityEnforcer("security_enforcer", config))
    coordinator.register_agent(LoopSimplifier("loop_simplifier", config))

    print(f"SNRE initialized with {len(coordinator.agents)} agents")

    return coordinator, config


def handle_start_command(args):
    """Handle start refactoring command"""
    coordinator, config = initialize_snre()

    agent_set = args.agents.split(',') if args.agents else ['security_enforcer']

    try:
        session_id = coordinator.start_refactor(args.path, agent_set)
        print(f"Started refactoring session: {session_id}")
        print(f"Target: {args.path}")
        print(f"Agents: {', '.join(agent_set)}")

        # Show initial status
        status = coordinator.get_session_status(session_id)
        print(f"Status: {status['status']}")
        print(f"Progress: {status['progress']}%")

    except Exception as e:
        print(f"Error starting refactoring: {str(e)}")
        sys.exit(1)


def handle_validate_command(args):
    """Handle code validation command"""
    try:
        with open(args.path) as f:
            code = f.read()

        # Basic syntax validation
        import ast
        try:
            ast.parse(code)
            print("Syntax validation: PASSED")
            print(f"File: {args.path}")
        except SyntaxError as e:
            print("Syntax validation: FAILED")
            print(f"Error: {e}")
            sys.exit(1)

    except FileNotFoundError:
        print(f"File not found: {args.path}")
        sys.exit(1)


def handle_status_command(args):
    """Handle status query command"""
    coordinator, config = initialize_snre()

    try:
        from uuid import UUID
        session_id = UUID(args.refactor_id)
        status = coordinator.get_session_status(session_id)

        print(f"Session: {args.refactor_id}")
        print(f"Status: {status['status']}")
        print(f"Progress: {status['progress']}%")
        print(f"Current iteration: {status['current_iteration']}")

    except ValueError:
        print(f"Invalid session ID: {args.refactor_id}")
        sys.exit(1)
    except Exception as e:
        print(f"Error getting status: {str(e)}")
        sys.exit(1)


def handle_result_command(args):
    """Handle result query command"""
    coordinator, config = initialize_snre()

    try:
        from uuid import UUID
        session_id = UUID(args.refactor_id)
        session = coordinator.get_session_result(session_id)

        print("=== REFACTORING RESULTS ===")
        print(f"Session: {args.refactor_id}")
        print(f"Status: {session.status.value}")
        print(f"Target: {session.target_path}")
        print(f"Agents: {', '.join(session.agent_set)}")

        if session.metrics:
            print("\nMetrics:")
            print(f"  Lines changed: {session.metrics.lines_changed}")
            print(f"  Complexity delta: {session.metrics.complexity_delta:.2f}")
            print(f"  Security improvements: {session.metrics.security_improvements}")
            print(f"  Performance gains: {session.metrics.performance_gains:.2f}")

        print(f"Evolution steps: {len(session.evolution_history)}")

        if session.evolution_history:
            print("Changes made:")
            for step in session.evolution_history:
                print(f"  - {step.agent}: {step.description} (confidence: {step.confidence:.2f})")

        if args.output:
            with open(args.output, 'w') as f:
                f.write(session.refactored_code or session.original_code)
            print(f"Refactored code written to: {args.output}")

    except ValueError:
        print(f"Invalid session ID: {args.refactor_id}")
        sys.exit(1)
    except Exception as e:
        print(f"Error getting results: {str(e)}")
        sys.exit(1)


def handle_show_command(args):
    """Handle show refactored code command"""
    coordinator, config = initialize_snre()

    try:
        from uuid import UUID
        session_id = UUID(args.refactor_id)
        session = coordinator.get_session_result(session_id)

        if session.status.value != "completed":
            print(f"Session not completed. Status: {session.status.value}")
            return

        refactored_code = session.refactored_code or session.original_code

        if args.diff:
            # Show diff between original and refactored
            from core.change_tracker import ChangeTracker
            tracker = ChangeTracker(config)
            diff = tracker.create_diff(session.original_code, refactored_code)

            print("=== CODE DIFFERENCES ===")
            print(f"Session: {args.refactor_id}")
            print(f"Target: {session.target_path}")
            print()
            print(diff)
        else:
            # Show refactored code
            print("=== REFACTORED CODE ===")
            print(f"Session: {args.refactor_id}")
            print(f"Target: {session.target_path}")
            print(f"Changes: {len(session.evolution_history)} modifications")
            print()

            if args.line_numbers:
                lines = refactored_code.split('\n')
                for i, line in enumerate(lines, 1):
                    print(f"{i:4d}: {line}")
            else:
                print(refactored_code)

    except ValueError:
        print(f"Invalid session ID format: {args.refactor_id}")
        sys.exit(1)
    except Exception as e:
        print(f"Error showing code: {str(e)}")
        sys.exit(1)


def handle_apply_command(args):
    """Handle apply refactored code to file command"""
    coordinator, config = initialize_snre()

    try:
        from uuid import UUID
        session_id = UUID(args.refactor_id)
        session = coordinator.get_session_result(session_id)

        if session.status.value != "completed":
            print(f"Cannot apply: Session not completed. Status: {session.status.value}")
            return

        if not session.refactored_code:
            print("No refactored code available to apply.")
            return

        # Check if file has been modified since refactoring started
        try:
            with open(session.target_path, encoding='utf-8') as f:
                current_content = f.read()

            if current_content != session.original_code and not args.force:
                print(f"WARNING: {session.target_path} has been modified since refactoring.")
                print("The original code no longer matches the file content.")
                print("Use --force to apply changes anyway, or start a new refactoring session.")
                return

        except FileNotFoundError:
            print(f"Error: Target file {session.target_path} not found.")
            return

        # Apply the changes
        success = coordinator.apply_session_to_file(session_id, not args.no_backup)

        if success:
            print(f"Successfully applied refactored code to {session.target_path}")
            if not args.no_backup:
                backup_path = f"{session.target_path}.backup"
                print(f"  Original file backed up to: {backup_path}")

            # Show summary of changes applied
            print(f"  Applied {len(session.evolution_history)} changes:")
            for step in session.evolution_history:
                print(f"    - {step.agent}: {step.description}")
        else:
            print("Failed to apply changes to file.")
            sys.exit(1)

    except ValueError:
        print(f"Invalid session ID format: {args.refactor_id}")
        sys.exit(1)
    except Exception as e:
        print(f"Error applying changes: {str(e)}")
        sys.exit(1)


def handle_list_command(args):
    """Handle list sessions command"""
    coordinator, config = initialize_snre()

    sessions = coordinator.list_active_sessions()

    if not sessions:
        print("No active sessions")
        return

    print("Active Sessions:")
    print("-" * 50)

    for session in sessions:
        print(f"ID: {session['refactor_id']}")
        print(f"Path: {session['target_path']}")
        print(f"Status: {session['status']}")
        print(f"Started: {session['started_at']}")
        print("-" * 50)


def handle_cancel_command(args):
    """Handle cancel session command"""
    coordinator, config = initialize_snre()

    try:
        from uuid import UUID
        session_id = UUID(args.refactor_id)
        success = coordinator.cancel_session(session_id)

        if success:
            print(f"Session {args.refactor_id} cancelled")
        else:
            print(f"Failed to cancel session {args.refactor_id}")

    except ValueError:
        print(f"Invalid session ID: {args.refactor_id}")
        sys.exit(1)


def main():
    """Main entry point for SNRE CLI"""
    parser = create_parser()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'start':
            handle_start_command(args)
        elif args.command == 'validate':
            handle_validate_command(args)
        elif args.command == 'status':
            handle_status_command(args)
        elif args.command == 'result':
            handle_result_command(args)
        elif args.command == 'show':
            handle_show_command(args)
        elif args.command == 'apply':
            handle_apply_command(args)
        elif args.command == 'list':
            handle_list_command(args)
        elif args.command == 'cancel':
            handle_cancel_command(args)
        else:
            print(f"Command '{args.command}' not implemented")
            print("Available commands: start, validate, status, result, show, apply, list, cancel")

    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
