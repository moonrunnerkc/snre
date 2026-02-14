"""
Change tracking and diff generation for SNRE
"""

import ast
import difflib
import re

from snre.models.config import Config
from snre.models.session import RefactorMetrics


class ChangeTracker:
    """Tracks and compares code changes"""

    def __init__(self, config: Config):
        self.config = config

    def create_diff(self, original: str, modified: str) -> str:
        """Create detailed diff between code versions"""
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
        """Calculate metrics for code changes"""
        original_lines = original.split("\n")
        modified_lines = modified.split("\n")

        lines_changed = self._count_changed_lines(original_lines, modified_lines)
        complexity_delta = self._calculate_complexity_delta(original, modified)
        security_improvements = self._count_security_improvements(original, modified)
        performance_gains = self._estimate_performance_gains(original, modified)

        return RefactorMetrics(
            lines_changed=lines_changed,
            complexity_delta=complexity_delta,
            security_improvements=security_improvements,
            performance_gains=performance_gains,
            agent_contributions={},
        )

    def validate_syntax(self, code: str, language: str = "python") -> bool:
        """Validate code syntax"""
        if language == "python":
            try:
                ast.parse(code)
                return True
            except SyntaxError:
                return False
        else:
            # Basic validation for other languages
            return len(code.strip()) > 0

    def measure_complexity(self, code: str) -> float:
        """Measure code complexity using simple heuristics"""
        if not code.strip():
            return 0.0

        complexity = 1.0

        # Count control structures
        complexity += code.count("if ")
        complexity += code.count("for ")
        complexity += code.count("while ")
        complexity += code.count("try:")
        complexity += code.count("except ")

        # Count function definitions
        complexity += code.count("def ")

        # Count nested structures (rough estimate)
        lines = code.split("\n")
        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent)

        complexity += max_indent / 4  # Assume 4 spaces per indent level

        return complexity

    def _count_changed_lines(
        self, original_lines: list[str], modified_lines: list[str]
    ) -> int:
        """Count number of changed lines"""
        differ = difflib.Differ()
        diff = list(differ.compare(original_lines, modified_lines))

        changed_lines = 0
        for line in diff:
            if line.startswith("+ ") or line.startswith("- "):
                changed_lines += 1

        return changed_lines

    def _calculate_complexity_delta(self, original: str, modified: str) -> float:
        """Calculate change in code complexity"""
        original_complexity = self.measure_complexity(original)
        modified_complexity = self.measure_complexity(modified)

        return modified_complexity - original_complexity

    def _count_security_improvements(self, original: str, modified: str) -> int:
        """Count security-related improvements"""
        security_patterns = [
            r"eval\(",
            r"exec\(",
            r'password\s*=\s*["\'][^"\']*["\']',
            r"cursor\.execute\([^)]*%",
            r"os\.system\([^)]*\+",
        ]

        original_issues = 0
        modified_issues = 0

        for pattern in security_patterns:
            original_issues += len(re.findall(pattern, original, re.IGNORECASE))
            modified_issues += len(re.findall(pattern, modified, re.IGNORECASE))

        return max(0, original_issues - modified_issues)

    def _estimate_performance_gains(self, original: str, modified: str) -> float:
        """Estimate performance improvements"""
        performance_indicators = {
            "list_comprehension": 0.2,  # Converting loops to list comprehensions
            "enumerate": 0.1,  # Using enumerate vs range(len())
            "generator": 0.3,  # Using generators vs lists
            "set_lookup": 0.4,  # Using sets for membership testing
        }

        gains = 0.0

        # Check for list comprehension improvements
        if (
            "[" in modified
            and "for" in modified
            and original.count("append") > modified.count("append")
        ):
            gains += performance_indicators["list_comprehension"]

        # Check for enumerate usage
        if "enumerate" in modified and "range(len(" in original:
            gains += performance_indicators["enumerate"]

        # Check for generator usage
        if "yield" in modified and "return" in original:
            gains += performance_indicators["generator"]

        return gains
