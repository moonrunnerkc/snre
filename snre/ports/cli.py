# Author: Bradley R. Kinnard
"""
Click-based CLI for SNRE. Single file, composable command groups.
Testable with click.testing.CliRunner.
"""

import json
import sys
from typing import Optional
from uuid import UUID

import click
import structlog

from snre.errors import SessionNotFoundError

logger = structlog.get_logger(__name__)


def _get_coordinator():
    """Lazy coordinator bootstrap -- avoids circular imports at module level."""
    from snre.di import Container

    container = Container()
    return container.coordinator


@click.group()
def cli() -> None:
    """snre -- swarm neural refactoring engine"""


@cli.command()
@click.option(
    "--path",
    required=True,
    type=click.Path(exists=True),
    help="target file to refactor",
)
@click.option("--agents", default="pattern_optimizer", help="comma-separated agent ids")
@click.option(
    "--config",
    "config_file",
    default=None,
    type=click.Path(exists=True),
    help="config override JSON",
)
@click.option("--verbose", is_flag=True, help="chattier output")
def start(path: str, agents: str, config_file: Optional[str], verbose: bool) -> None:
    """Start a refactoring session."""
    coordinator = _get_coordinator()
    agent_list = [a.strip() for a in agents.split(",")]

    config_overrides: dict = {}
    if config_file:
        with open(config_file) as fh:
            config_overrides = json.load(fh)

    session_id = coordinator.start_refactor(path, agent_list, config_overrides or None)

    click.echo(f"Started refactoring session: {session_id}")
    click.echo(f"Target: {path}")
    click.echo(f"Agents: {', '.join(agent_list)}")

    if verbose:
        click.echo(f"Config overrides: {config_overrides}")


@cli.command()
@click.argument("refactor_id")
def status(refactor_id: str) -> None:
    """Get session status."""
    coordinator = _get_coordinator()
    try:
        sid = UUID(refactor_id)
    except ValueError:
        click.echo(f"Invalid session ID format: {refactor_id}", err=True)
        sys.exit(1)

    try:
        info = coordinator.get_session_status(sid)
    except SessionNotFoundError:
        click.echo(f"Session not found: {refactor_id}", err=True)
        sys.exit(1)

    click.echo(f"Session ID: {refactor_id}")
    click.echo(f"Status: {info['status']}")
    click.echo(f"Progress: {info['progress']}%")
    click.echo(f"Current Iteration: {info['current_iteration']}")

    if info.get("agent_votes"):
        click.echo("\nAgent Votes:")
        for agent_id, vote_data in info["agent_votes"].items():
            click.echo(f"  {agent_id}: {vote_data['confidence']:.2f} confidence")


@cli.command()
@click.argument("refactor_id")
@click.option("--output", default=None, help="write results to file")
def result(refactor_id: str, output: Optional[str]) -> None:
    """Get session results."""
    coordinator = _get_coordinator()
    try:
        sid = UUID(refactor_id)
    except ValueError:
        click.echo(f"Invalid session ID format: {refactor_id}", err=True)
        sys.exit(1)

    try:
        session = coordinator.get_session_result(sid)
    except SessionNotFoundError:
        click.echo(f"Session not found: {refactor_id}", err=True)
        sys.exit(1)

    if session.status.value != "completed":
        click.echo(f"Session not completed. Status: {session.status.value}")
        return

    if output:
        with open(output, "w") as fh:
            fh.write(session.refactored_code or session.original_code)
        click.echo(f"Results written to: {output}")
        return

    click.echo("=== REFACTORING RESULTS ===")
    click.echo(f"Session: {refactor_id}")
    click.echo(f"Status: {session.status.value}")
    click.echo(f"Target: {session.target_path}")
    click.echo(f"Agents: {', '.join(session.agent_set)}")

    if session.metrics:
        click.echo("\nMetrics:")
        click.echo(f"  Lines changed: {session.metrics.lines_changed}")
        click.echo(f"  Complexity delta: {session.metrics.complexity_delta:.2f}")
        click.echo(f"  Security improvements: {session.metrics.security_improvements}")
        click.echo(f"  Performance gains: {session.metrics.performance_gains:.2f}")

    click.echo(f"Evolution steps: {len(session.evolution_history)}")
    if session.evolution_history:
        click.echo("Changes made:")
        for step in session.evolution_history:
            click.echo(
                f"  - {step.agent}: {step.description} (confidence: {step.confidence:.2f})"
            )


@cli.command("list")
def list_sessions() -> None:
    """List active sessions."""
    coordinator = _get_coordinator()
    sessions = coordinator.list_active_sessions()

    if not sessions:
        click.echo("No active sessions")
        return

    click.echo("Active Sessions:")
    click.echo("-" * 50)
    for sess in sessions:
        click.echo(f"ID: {sess['refactor_id']}")
        click.echo(f"Path: {sess['target_path']}")
        click.echo(f"Status: {sess['status']}")
        click.echo(f"Started: {sess['started_at']}")
        click.echo("-" * 50)


@cli.command()
@click.argument("refactor_id")
def cancel(refactor_id: str) -> None:
    """Cancel an active session."""
    coordinator = _get_coordinator()
    try:
        sid = UUID(refactor_id)
    except ValueError:
        click.echo(f"Invalid session ID format: {refactor_id}", err=True)
        sys.exit(1)

    success = coordinator.cancel_session(sid)
    if success:
        click.echo(f"Session {refactor_id} cancelled")
    else:
        click.echo(f"Failed to cancel session {refactor_id}")
        sys.exit(1)


@cli.command()
@click.option(
    "--path",
    required=True,
    type=click.Path(exists=True),
    help="target file to validate",
)
def validate(path: str) -> None:
    """Validate code syntax and measure complexity."""
    from core.change_tracker import ChangeTracker
    from snre.models.config import SNREConfig

    tracker = ChangeTracker(SNREConfig())

    with open(path) as fh:
        code = fh.read()

    is_valid = tracker.validate_syntax(code)
    complexity = tracker.measure_complexity(code)

    click.echo(f"File: {path}")
    click.echo(f"Syntax valid: {is_valid}")
    click.echo(f"Complexity score: {complexity:.2f}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="API bind host")
@click.option("--port", default=8000, type=int, help="API bind port")
def api(host: str, port: int) -> None:
    """Start the SNRE REST API server."""
    import uvicorn

    from snre.ports.api import create_app

    coordinator = _get_coordinator()
    app = create_app(coordinator)

    click.echo(f"Starting SNRE API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
