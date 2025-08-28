"""
Pattern optimization agent for SNRE
"""


import libcst as cst

from agents.base_agent import BaseAgent
from contracts import AgentAnalysis, Change, ChangeType, Config


class PatternOptimizer(BaseAgent):
    """Agent for optimizing code patterns"""

    def __init__(self, agent_id: str, config: Config):
        super().__init__(agent_id, config)
        self._priority = 7
        self._confidence_threshold = 0.6

    def analyze(self, code: str) -> AgentAnalysis:
        """Analyze code for optimization opportunities"""
        try:
            tree = self._parse_code(code)
            patterns = self.detect_patterns(code)
            complexity = self._calculate_complexity(tree)

            return AgentAnalysis(
                agent_id=self.agent_id,
                issues_found=len(patterns),
                complexity_score=complexity,
                security_risks=[],
                optimization_opportunities=patterns,
                confidence=0.8
            )
        except Exception:
            return AgentAnalysis(
                agent_id=self.agent_id,
                issues_found=0,
                complexity_score=0.0,
                security_risks=[],
                optimization_opportunities=[],
                confidence=0.0
            )

    def suggest_changes(self, code: str) -> list[Change]:
        """Suggest specific optimization changes"""
        changes = []
        lines = code.split('\n')

        for i, line in enumerate(lines):
            # Detect list comprehension opportunities
            if 'for' in line and 'append' in line and i + 1 < len(lines):
                if '.append(' in lines[i + 1]:
                    change = Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.OPTIMIZATION,
                        original_code=f"{line}\n{lines[i + 1]}",
                        modified_code=self._suggest_list_comprehension(line, lines[i + 1]),
                        line_start=i,
                        line_end=i + 1,
                        confidence=0.7,
                        description="Convert to list comprehension",
                        impact_score=0.6
                    )
                    changes.append(change)

            # Detect unnecessary variable assignments
            if '=' in line and line.strip().endswith('None'):
                change = Change(
                    agent_id=self.agent_id,
                    change_type=ChangeType.OPTIMIZATION,
                    original_code=line,
                    modified_code="# Removed unnecessary None assignment",
                    line_start=i,
                    line_end=i,
                    confidence=0.5,
                    description="Remove unnecessary None assignment",
                    impact_score=0.3
                )
                changes.append(change)

        return changes

    def vote(self, changes: list[Change]) -> dict[str, float]:
        """Vote on proposed changes from all agents"""
        votes = {}

        for change in changes:
            vote_key = f"{change.agent_id}_{change.line_start}_{change.change_type.value}"

            # Vote higher for optimization changes
            if change.change_type == ChangeType.OPTIMIZATION:
                votes[vote_key] = min(change.confidence * 1.2, 1.0)
            else:
                votes[vote_key] = change.confidence * 0.8

        return votes

    def validate_result(self, original: str, modified: str) -> bool:
        """Validate that changes improve code quality"""
        try:
            # Check syntax validity
            cst.parse_module(modified)

            # Basic validation: modified code should be different
            if original.strip() == modified.strip():
                return False

            return True
        except Exception:
            return False

    def get_priority(self) -> int:
        """Get agent priority for consensus"""
        return self._priority

    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold"""
        return self._confidence_threshold

    def detect_patterns(self, code: str) -> list[str]:
        """Detect optimization patterns in code"""
        patterns = []
        lines = code.split('\n')

        for _i, line in enumerate(lines):
            if 'for' in line and '.append(' in code[code.find(line):]:
                patterns.append("list_comprehension_opportunity")

            if 'if' in line and 'else:' in code and 'return' in line:
                patterns.append("ternary_operator_opportunity")

            if line.strip().startswith('temp_') or line.strip().startswith('tmp_'):
                patterns.append("unnecessary_temp_variable")

        return patterns

    def _suggest_list_comprehension(self, for_line: str, append_line: str) -> str:
        """Suggest list comprehension replacement"""
        # Simple pattern matching for common cases
        if 'for' in for_line and '.append(' in append_line:
            return f"# TODO: Convert to list comprehension: {for_line.strip()}"
        return for_line
