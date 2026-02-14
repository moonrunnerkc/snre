# Author: Bradley R. Kinnard
"""
Stateless change tracker -- diffs and metrics with no mutable state.
"""

import ast
import difflib
import re

from snre.models.session import RefactorMetrics


class ChangeTracker:
    """Tracks and compares code changes. Stateless utility."""

    def create_diff(self, original: str, modified: str) -> str:
        """Unified diff between two code strings."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="original",
            tofile="modified",
            lineterm="",
        )
        return "".join(diff)

    def calculate_metrics(self, original: str, modified: str) -> RefactorMetrics:
        """Compute before/after metrics."""
        original_lines = original.split("\n")
        modified_lines = modified.split("\n")

        lines_changed = self._count_changed_lines(original_lines, modified_lines)
        complexity_delta = self._complexity_delta(original, modified)
        security_improvements = self._security_improvements(original, modified)
        performance_gains = self._performance_gains(original, modified)

        return RefactorMetrics(
            lines_changed=lines_changed,
            complexity_delta=complexity_delta,
            security_improvements=security_improvements,
            performance_gains=performance_gains,
            agent_contributions={},
        )

    def validate_syntax(self, code: str, language: str = "python") -> bool:
        """Check if code parses without errors."""
        if language == "python":
            try:
                ast.parse(code)
                return True
            except SyntaxError:
                return False
        return len(code.strip()) > 0

    def measure_complexity(self, code: str) -> float:
        """Simple heuristic complexity score."""
        if not code.strip():
            return 0.0

        complexity = 1.0
        complexity += code.count("if ")
        complexity += code.count("for ")
        complexity += code.count("while ")
        complexity += code.count("try:")
        complexity += code.count("except ")
        complexity += code.count("def ")

        max_indent = 0
        for line in code.split("\n"):
            stripped = line.lstrip()
            if stripped:
                indent = len(line) - len(stripped)
                max_indent = max(max_indent, indent)

        complexity += max_indent / 4
        return complexity

    # ---- internals ----

    def _count_changed_lines(self, original: list[str], modified: list[str]) -> int:
        differ = difflib.Differ()
        diff = list(differ.compare(original, modified))
        return sum(1 for line in diff if line.startswith("+ ") or line.startswith("- "))

    def _complexity_delta(self, original: str, modified: str) -> float:
        return self.measure_complexity(modified) - self.measure_complexity(original)

    def _security_improvements(self, original: str, modified: str) -> int:
        patterns = [
            r"eval\(",
            r"exec\(",
            r'password\s*=\s*["\'][^"\']*["\']',
            r"cursor\.execute\([^)]*%",
            r"os\.system\([^)]*\+",
        ]
        original_issues = sum(
            len(re.findall(p, original, re.IGNORECASE)) for p in patterns
        )
        modified_issues = sum(
            len(re.findall(p, modified, re.IGNORECASE)) for p in patterns
        )
        return max(0, original_issues - modified_issues)

    def _performance_gains(self, original: str, modified: str) -> float:
        gains = 0.0
        if (
            "[" in modified
            and "for" in modified
            and original.count("append") > modified.count("append")
        ):
            gains += 0.2
        if "enumerate" in modified and "range(len(" in original:
            gains += 0.1
        if "yield" in modified and "return" in original:
            gains += 0.3
        return gains
