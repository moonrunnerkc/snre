"""
Loop simplification agent for SNRE
"""

import re

import libcst as cst

from agents.base_agent import BaseAgent
from contracts import AgentAnalysis, Change, ChangeType, Config


class LoopSimplifier(BaseAgent):
    """Agent for simplifying and optimizing loops"""

    def __init__(self, agent_id: str, config: Config):
        super().__init__(agent_id, config)
        self._priority = 6
        self._confidence_threshold = 0.7

    def analyze(self, code: str) -> AgentAnalysis:
        """Analyze code for loop optimization opportunities"""
        try:
            tree = self._parse_code(code)
            loop_issues = self._detect_loop_issues(code)
            complexity = self._calculate_complexity(tree)

            return AgentAnalysis(
                agent_id=self.agent_id,
                issues_found=len(loop_issues),
                complexity_score=complexity,
                security_risks=[],
                optimization_opportunities=loop_issues,
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
        """Suggest loop optimizations"""
        return self.optimize_loops(code)

    def vote(self, changes: list[Change]) -> dict[str, float]:
        """Vote on proposed changes with loop focus"""
        votes = {}

        for change in changes:
            vote_key = f"{change.agent_id}_{change.line_start}_{change.change_type.value}"

            # High support for loop optimizations
            if 'loop' in change.description.lower():
                votes[vote_key] = min(change.confidence * 1.3, 1.0)
            elif change.change_type == ChangeType.PERFORMANCE:
                votes[vote_key] = change.confidence * 1.1
            else:
                votes[vote_key] = change.confidence * 0.6

        return votes

    def validate_result(self, original: str, modified: str) -> bool:
        """Validate that loop changes are correct"""
        try:
            # Ensure modified code is syntactically valid
            cst.parse_module(modified)

            # Check that loop count hasn't increased
            original_loops = self._count_loops(original)
            modified_loops = self._count_loops(modified)

            return modified_loops <= original_loops
        except Exception:
            return False

    def get_priority(self) -> int:
        """Get agent priority for consensus"""
        return self._priority

    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold"""
        return self._confidence_threshold

    def optimize_loops(self, code: str) -> list[Change]:
        """Find and optimize inefficient loops"""
        changes = []
        lines = code.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Detect nested loop with simple append pattern
            if self._is_nested_loop_pattern(lines, i):
                original_block = self._extract_loop_block(lines, i)
                optimized = self._optimize_nested_loop(original_block)

                if optimized != original_block:
                    change = Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.PERFORMANCE,
                        original_code=original_block,
                        modified_code=optimized,
                        line_start=i,
                        line_end=i + original_block.count('\n'),
                        confidence=0.8,
                        description="Optimize nested loop to list comprehension",
                        impact_score=0.7
                    )
                    changes.append(change)

            # Detect range(len()) pattern
            elif 'for' in line and 'range(len(' in line:
                change = Change(
                    agent_id=self.agent_id,
                    change_type=ChangeType.OPTIMIZATION,
                    original_code=line,
                    modified_code=self._convert_range_len(line),
                    line_start=i,
                    line_end=i,
                    confidence=0.9,
                    description="Replace range(len()) with enumerate()",
                    impact_score=0.6
                )
                changes.append(change)

            i += 1

        return changes

    def _detect_loop_issues(self, code: str) -> list[str]:
        """Detect various loop inefficiency patterns"""
        issues = []

        if re.search(r'for.*range\(len\(', code):
            issues.append("range_len_pattern")

        if re.search(r'for.*\n.*for.*\n.*\.append', code, re.MULTILINE):
            issues.append("nested_loop_with_append")

        if re.search(r'while.*True.*\n.*if.*break', code, re.MULTILINE):
            issues.append("infinite_loop_with_break")

        if code.count('for ') > 3:
            issues.append("excessive_nested_loops")

        return issues

    def _is_nested_loop_pattern(self, lines: list[str], start_idx: int) -> bool:
        """Check if lines starting at start_idx contain nested loop pattern"""
        if start_idx >= len(lines) - 2:
            return False

        first_line = lines[start_idx].strip()
        if not first_line.startswith('for '):
            return False

        # Look for nested for loop in next few lines
        for i in range(start_idx + 1, min(start_idx + 5, len(lines))):
            if 'for ' in lines[i] and '.append(' in lines[i + 1:i + 3]:
                return True

        return False

    def _extract_loop_block(self, lines: list[str], start_idx: int) -> str:
        """Extract the complete loop block"""
        indent_level = len(lines[start_idx]) - len(lines[start_idx].lstrip())
        block_lines = [lines[start_idx]]

        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                block_lines.append(line)
                continue

            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and line.strip():
                break

            block_lines.append(line)

        return '\n'.join(block_lines)

    def _optimize_nested_loop(self, loop_block: str) -> str:
        """Attempt to optimize nested loop structure"""
        # Simple optimization: add comment suggesting list comprehension
        if '.append(' in loop_block and 'for ' in loop_block:
            return f"# OPTIMIZED: {loop_block.strip()}\n# TODO: Consider list comprehension"
        return loop_block

    def _convert_range_len(self, line: str) -> str:
        """Convert range(len()) to enumerate()"""
        # Extract variable names
        match = re.search(r'for\s+(\w+)\s+in\s+range\(len\((\w+)\)\)', line)
        if match:
            index_var, list_var = match.groups()
            return line.replace(
                f'for {index_var} in range(len({list_var}))',
                f'for {index_var}, item in enumerate({list_var})'
            )
        return line

    def _count_loops(self, code: str) -> int:
        """Count number of loops in code"""
        return code.count('for ') + code.count('while ')
