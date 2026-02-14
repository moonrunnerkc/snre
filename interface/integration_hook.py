"""
Git and IDE integration hooks for SNRE
"""

import logging
import os
import subprocess
from uuid import UUID

from snre.models.config import Config

logger = logging.getLogger(__name__)


class IntegrationHook:
    """Git and IDE integration hooks"""

    def __init__(self, coordinator, config: Config):
        self.coordinator = coordinator
        self.config = config

    def setup_git_hooks(self, repo_path: str) -> bool:
        """Setup git pre-commit and post-commit hooks"""
        hooks_dir = os.path.join(repo_path, ".git", "hooks")

        if not os.path.exists(hooks_dir):
            return False

        try:
            # Create pre-commit hook
            pre_commit_path = os.path.join(hooks_dir, "pre-commit")
            with open(pre_commit_path, "w") as f:
                f.write(self._generate_pre_commit_hook())
            os.chmod(pre_commit_path, 0o755)

            # Create post-commit hook
            post_commit_path = os.path.join(hooks_dir, "post-commit")
            with open(post_commit_path, "w") as f:
                f.write(self._generate_post_commit_hook())
            os.chmod(post_commit_path, 0o755)

            return True

        except Exception:
            return False

    def validate_pre_commit(self, staged_files: list[str]) -> bool:
        """Validate staged files before commit"""
        from core.change_tracker import ChangeTracker

        tracker = ChangeTracker(self.config)

        for file_path in staged_files:
            if file_path.endswith(".py"):
                try:
                    with open(file_path) as f:
                        code = f.read()

                    if not tracker.validate_syntax(code):
                        logger.error("syntax error in %s", file_path)
                        return False

                except Exception as e:
                    logger.error("error validating %s: %s", file_path, e)
                    return False

        return True

    def trigger_post_commit(self, changed_files: list[str]) -> UUID:
        """Trigger refactoring after successful commit"""
        # Filter to Python files
        python_files = [f for f in changed_files if f.endswith(".py")]

        if python_files and self.config.git_auto_commit:
            # Start refactoring on the first Python file
            session_id = self.coordinator.start_refactor(
                python_files[0],
                ["security_enforcer", "pattern_optimizer"],
                {"auto_triggered": True},
            )
            return session_id

    def setup_ide_integration(self, ide_type: str, project_path: str) -> bool:
        """Setup IDE integration for real-time suggestions"""
        if ide_type.lower() == "vscode":
            return self._setup_vscode_integration(project_path)
        elif ide_type.lower() == "vim":
            return self._setup_vim_integration(project_path)
        else:
            return False

    def _generate_pre_commit_hook(self) -> str:
        """Generate pre-commit hook script"""
        return r"""#!/bin/bash
# SNRE Pre-commit Hook

echo "Running SNRE validation..."

# Get list of staged Python files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -n "$STAGED_FILES" ]; then
    for file in $STAGED_FILES; do
        echo "Validating $file..."
        python -m py_compile "$file"
        if [ $? -ne 0 ]; then
            echo "Syntax error in $file - commit aborted"
            exit 1
        fi
    done
fi

echo "SNRE validation passed"
exit 0
"""

    def _generate_post_commit_hook(self) -> str:
        """Generate post-commit hook script"""
        return r"""#!/bin/bash
# SNRE Post-commit Hook

echo "Running SNRE auto-refactoring..."

# Get list of changed Python files in last commit
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD | grep '\.py$')

if [ -n "$CHANGED_FILES" ]; then
    echo "Starting SNRE refactoring for: $CHANGED_FILES"
    # This would call the SNRE CLI in a real implementation
    # snre start --path $CHANGED_FILES --agents security_enforcer,pattern_optimizer
fi
"""

    def _setup_vscode_integration(self, project_path: str) -> bool:
        """Setup VS Code integration"""
        vscode_dir = os.path.join(project_path, ".vscode")
        os.makedirs(vscode_dir, exist_ok=True)

        settings_path = os.path.join(vscode_dir, "settings.json")

        settings = {
            "snre.enabled": True,
            "snre.autoRefactor": False,
            "snre.agents": ["security_enforcer", "pattern_optimizer"],
            "snre.apiEndpoint": "http://localhost:8000",
        }

        try:
            import json

            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception:
            return False

    def _setup_vim_integration(self, project_path: str) -> bool:
        """Setup Vim integration"""
        vimrc_path = os.path.join(project_path, ".vimrc.local")

        vim_config = """
" SNRE Integration
function! SNRERefactor()
    let l:current_file = expand('%:p')
    call system('snre start --path ' . shellescape(l:current_file) . ' --agents pattern_optimizer')
endfunction

command! SNRERefactor call SNRERefactor()
nnoremap <leader>sr :SNRERefactor<CR>
"""

        try:
            with open(vimrc_path, "w") as f:
                f.write(vim_config)
            return True
        except Exception:
            return False

    def get_staged_files(self, repo_path: str) -> list[str]:
        """Get list of staged files in git repository"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return result.stdout.strip().split("\n")
            else:
                return []

        except Exception:
            return []
