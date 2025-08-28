"""
Base agent implementation for SNRE
"""

from abc import ABC, abstractmethod

import libcst as cst

from contracts import AgentAnalysis, BaseAgent, Change, Config


class BaseAgent(ABC):
    """Abstract base class for all refactoring agents"""

    def __init__(self, agent_id: str, config: Config):
        self.agent_id = agent_id
        self.config = config
        self._priority = 5
        self._confidence_threshold = 0.5

    @abstractmethod
    def analyze(self, code: str) -> AgentAnalysis:
        """Analyze code and identify issues"""
        pass

    @abstractmethod
    def suggest_changes(self, code: str) -> list[Change]:
        """Suggest specific code changes"""
        pass

    @abstractmethod
    def vote(self, changes: list[Change]) -> dict[str, float]:
        """Vote on proposed changes from all agents"""
        pass

    @abstractmethod
    def validate_result(self, original: str, modified: str) -> bool:
        """Validate that changes are safe and beneficial"""
        pass

    def get_priority(self) -> int:
        """Get agent priority for consensus"""
        return self._priority

    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold"""
        return self._confidence_threshold

    def _parse_code(self, code: str) -> cst.Module:
        """Parse Python code using libcst"""
        try:
            return cst.parse_module(code)
        except Exception as e:
            from contracts import SNRESyntaxError
            raise SNRESyntaxError(f"Failed to parse code: {str(e)}")

    def _calculate_complexity(self, tree: cst.Module) -> float:
        """Calculate basic cyclomatic complexity"""

        class ComplexityCalculator(cst.CSTVisitor):
            def __init__(self):
                self.complexity = 1

            def visit_If(self, node: cst.If) -> None:
                self.complexity += 1

            def visit_For(self, node: cst.For) -> None:
                self.complexity += 1

            def visit_While(self, node: cst.While) -> None:
                self.complexity += 1

            def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
                self.complexity += 1

        visitor = ComplexityCalculator()
        tree.visit(visitor)
        return visitor.complexity
