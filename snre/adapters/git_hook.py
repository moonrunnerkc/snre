# Author: Bradley R. Kinnard
"""
Git integration adapter -- replaces the old IntegrationHook.
Handles branch creation, auto-commit, and pre/post-commit hooks.
"""

import os
import subprocess

import structlog

logger = structlog.get_logger(__name__)


class GitHook:
    """Git integration for SNRE refactoring sessions."""

    def __init__(self, auto_commit: bool = False, create_branch: bool = True) -> None:
        self.auto_commit = auto_commit
        self.create_branch = create_branch

    def create_refactor_branch(self, repo_path: str, branch_name: str) -> bool:
        """Create and checkout a new branch for refactoring."""
        try:
            subprocess.run(
                ["git", "-C", repo_path, "checkout", "-b", branch_name],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("git.branch_created", branch=branch_name, repo=repo_path)
            return True
        except subprocess.CalledProcessError as exc:
            logger.warning("git.branch_failed", branch=branch_name, error=exc.stderr)
            return False

    def commit_changes(self, repo_path: str, message: str) -> bool:
        """Stage all changes and commit."""
        try:
            subprocess.run(
                ["git", "-C", repo_path, "add", "-A"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", repo_path, "commit", "-m", message],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("git.committed", message=message)
            return True
        except subprocess.CalledProcessError as exc:
            logger.warning("git.commit_failed", error=exc.stderr)
            return False

    def setup_hooks(self, repo_path: str) -> bool:
        """Install pre-commit and post-commit hooks."""
        hooks_dir = os.path.join(repo_path, ".git", "hooks")
        if not os.path.isdir(hooks_dir):
            return False

        pre_commit = os.path.join(hooks_dir, "pre-commit")
        with open(pre_commit, "w") as fh:
            fh.write(
                '#!/bin/sh\n# SNRE pre-commit hook\npython -m snre validate --path "$@"\n'
            )
        os.chmod(pre_commit, 0o755)

        return True
