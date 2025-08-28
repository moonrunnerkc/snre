"""
Command line interface for SNRE
"""

import argparse
import json
import sys
from typing import Any, Optional
from uuid import UUID

from contracts import Config, SessionNotFoundError


class CLIInterface:
    """Command line interface for SNRE"""

    def __init__(self, coordinator, config: Config):
        self.coordinator = coordinator
        self.config = config

    def run(self, args: list[str] = None) -> None:
        """Run CLI with provided arguments"""
        if args is None:
            args = sys.argv[1:]  # Use all args from command line

        parser = self._create_parser()
        parsed_args = parser.parse_args(args)

        try:
            if parsed_args.command == 'start':
                self.handle_start_command(vars(parsed_args))
            elif parsed_args.command == 'status':
                self.handle_status_command(parsed_args.refactor_id)
            elif parsed_args.command == 'result':
                self.handle_result_command(parsed_args.refactor_id, parsed_args.output)
            elif parsed_args.command == 'show':
                self.handle_show_command(parsed_args.refactor_id, parsed_args.diff, parsed_args.line_numbers)
            elif parsed_args.command == 'apply':
                self.handle_apply_command(parsed_args.refactor_id, getattr(parsed_args, 'no_backup', False), parsed_args.force)
            elif parsed_args.command == 'list':
                self.handle_list_command()
            elif parsed_args.command == 'cancel':
                self.handle_cancel_command(parsed_args.refactor_id)
            elif parsed_args.command == 'validate':
                self.handle_validate_command(parsed_args.path)
            else:
                parser.print_help()

        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)

    def handle_start_command(self, args: dict[str, Any]) -> None:
        """Handle start refactoring command"""
        target_path = args['path']
        agent_set = args['agents'].split(',') if args['agents'] else ['pattern_optimizer']
        config_overrides = {}

        if args.get('config'):
            with open(args['config']) as f:
                config_overrides = json.load(f)

        try:
            session_id = self.coordinator.start_refactor(
                target_path, agent_set, config_overrides
            )

            print(f"Started refactoring session: {session_id}")
            print(f"Target: {target_path}")
            print(f"Agents: {', '.join(agent_set)}")

            if args.get('verbose'):
                print(f"Config overrides: {config_overrides}")

        except Exception as e:
            print(f"Failed to start refactoring: {str(e)}", file=sys.stderr)
            sys.exit(1)

    def handle_status_command(self, refactor_id: str) -> None:
        """Handle status query command"""
        try:
            session_id = UUID(refactor_id)
            status = self.coordinator.get_session_status(session_id)

            print(f"Session ID: {refactor_id}")
            print(f"Status: {status['status']}")
            print(f"Progress: {status['progress']}%")
            print(f"Current Iteration: {status['current_iteration']}")

            if status['agent_votes']:
                print("\nAgent Votes:")
                for agent_id, vote_data in status['agent_votes'].items():
                    print(f"  {agent_id}: {vote_data['confidence']:.2f} confidence")

        except ValueError:
            print(f"Invalid session ID format: {refactor_id}", file=sys.stderr)
            sys.exit(1)
        except SessionNotFoundError:
            print(f"Session not found: {refactor_id}", file=sys.stderr)
            sys.exit(1)

    def handle_result_command(self, refactor_id: str, output_file: Optional[str] = None) -> None:
        """Handle result query command"""
        try:
            session_id = UUID(refactor_id)
            session = self.coordinator.get_session_result(session_id)

            if session.status.value != "completed":
                print(f"Session not completed. Status: {session.status.value}")
                return

            if output_file:
                with open(output_file, 'w') as f:
                    f.write(session.refactored_code or session.original_code)
                print(f"Results written to: {output_file}")
            else:
                print("=== REFACTORING RESULTS ===")
                print(f"Session: {refactor_id}")
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

        except ValueError:
            print(f"Invalid session ID format: {refactor_id}", file=sys.stderr)
            sys.exit(1)
        except SessionNotFoundError:
            print(f"Session not found: {refactor_id}", file=sys.stderr)
            sys.exit(1)

    def handle_show_command(self, refactor_id: str, show_diff: bool = False,
                           show_line_numbers: bool = False) -> None:
        """Handle show refactored code command"""
        try:
            session_id = UUID(refactor_id)
            session = self.coordinator.get_session_result(session_id)

            if session.status.value != "completed":
                print(f"Session not completed. Status: {session.status.value}")
                return

            refactored_code = session.refactored_code or session.original_code

            if show_diff:
                # Show diff between original and refactored
                from core.change_tracker import ChangeTracker
                tracker = ChangeTracker(self.config)
                diff = tracker.create_diff(session.original_code, refactored_code)

                print("=== CODE DIFFERENCES ===")
                print(f"Session: {refactor_id}")
                print(f"Target: {session.target_path}")
                print()
                print(diff)
            else:
                # Show refactored code
                print("=== REFACTORED CODE ===")
                print(f"Session: {refactor_id}")
                print(f"Target: {session.target_path}")
                print(f"Changes: {len(session.evolution_history)} modifications")
                print()

                if show_line_numbers:
                    lines = refactored_code.split('\n')
                    for i, line in enumerate(lines, 1):
                        print(f"{i:4d}: {line}")
                else:
                    print(refactored_code)

        except ValueError:
            print(f"Invalid session ID format: {refactor_id}", file=sys.stderr)
            sys.exit(1)
        except SessionNotFoundError:
            print(f"Session not found: {refactor_id}", file=sys.stderr)
            sys.exit(1)
    def handle_apply_command(self, refactor_id: str, no_backup: bool = False, force: bool = False) -> None:
        """Handle apply refactored code to file command"""
        try:
            session_id = UUID(refactor_id)
            session = self.coordinator.get_session_result(session_id)

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

                if current_content != session.original_code and not force:
                    print(f"WARNING: {session.target_path} has been modified since refactoring.")
                    print("The original code no longer matches the file content.")
                    print("Use --force to apply changes anyway, or start a new refactoring session.")
                    return

            except FileNotFoundError:
                print(f"Error: Target file {session.target_path} not found.")
                return

            # Apply the changes
            success = self.coordinator.apply_session_to_file(session_id, not no_backup)

            if success:
                print(f"Successfully applied refactored code to {session.target_path}")
                if not no_backup:
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
            print(f"Invalid session ID format: {refactor_id}", file=sys.stderr)
            sys.exit(1)
        except SessionNotFoundError:
            print(f"Session not found: {refactor_id}", file=sys.stderr)
            sys.exit(1)

    def handle_list_command(self) -> None:
        """Handle list sessions command"""
        sessions = self.coordinator.list_active_sessions()

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

    def handle_cancel_command(self, refactor_id: str) -> None:
        """Handle cancel session command"""
        try:
            session_id = UUID(refactor_id)
            success = self.coordinator.cancel_session(session_id)

            if success:
                print(f"Session {refactor_id} cancelled")
            else:
                print(f"Failed to cancel session {refactor_id}")

        except ValueError:
            print(f"Invalid session ID format: {refactor_id}", file=sys.stderr)
            sys.exit(1)

    def handle_validate_command(self, target_path: str) -> None:
        """Handle code validation command"""
        try:
            with open(target_path) as f:
                code = f.read()

            from core.change_tracker import ChangeTracker
            tracker = ChangeTracker(self.config)

            is_valid = tracker.validate_syntax(code)
            complexity = tracker.measure_complexity(code)

            print(f"File: {target_path}")
            print(f"Syntax valid: {is_valid}")
            print(f"Complexity score: {complexity:.2f}")

        except FileNotFoundError:
            print(f"File not found: {target_path}", file=sys.stderr)
            sys.exit(1)

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create command line argument parser"""
        parser = argparse.ArgumentParser(description="SNRE - Swarm Neural Refactoring Engine")
        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Start command
        start_parser = subparsers.add_parser('start', help='Start refactoring session')
        start_parser.add_argument('--path', required=True, help='Target code path')
        start_parser.add_argument('--agents', help='Comma-separated list of agents')
        start_parser.add_argument('--config', help='Custom configuration file')
        start_parser.add_argument('--verbose', action='store_true', help='Verbose output')
        start_parser.add_argument('--dry-run', action='store_true', help='Show proposed changes only')

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
