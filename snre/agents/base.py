# Author: Bradley R. Kinnard
"""
Shared helpers for agents -- code parsing, complexity calculation.
Not an ABC. Agents can use these as a mixin or call them directly.
"""

import libcst as cst

from snre.errors import SNRESyntaxError


def parse_code(code: str) -> cst.Module:
    """Parse Python source into a libcst tree. Raises SNRESyntaxError on failure."""
    try:
        return cst.parse_module(code)
    except Exception as e:
        raise SNRESyntaxError(f"Failed to parse code: {e}")


def calculate_complexity(tree: cst.Module) -> float:
    """Basic cyclomatic complexity from a libcst tree."""

    class _Counter(cst.CSTVisitor):
        def __init__(self) -> None:
            self.complexity = 1

        def visit_If(self, node: cst.If) -> None:
            self.complexity += 1

        def visit_For(self, node: cst.For) -> None:
            self.complexity += 1

        def visit_While(self, node: cst.While) -> None:
            self.complexity += 1

        def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
            self.complexity += 1

    visitor = _Counter()
    tree.visit(visitor)
    return visitor.complexity
