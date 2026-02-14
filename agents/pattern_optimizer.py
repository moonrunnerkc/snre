"""
Pattern optimization agent for SNRE
"""

import re
from typing import Optional

import libcst as cst

from agents.base_agent import BaseAgent
from snre.models.changes import AgentAnalysis
from snre.models.changes import Change
from snre.models.config import Config
from snre.models.enums import ChangeType


class PatternOptimizer(BaseAgent):
    """Agent for optimizing code patterns"""

    def __init__(self, agent_id: str, config: Config):
        super().__init__(agent_id, config)

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
                confidence=0.8 if patterns else 0.5,
            )
        except Exception:
            return AgentAnalysis(
                agent_id=self.agent_id,
                issues_found=0,
                complexity_score=0.0,
                security_risks=[],
                optimization_opportunities=[],
                confidence=0.0,
            )

    def detect_patterns(self, code: str) -> list[str]:
        """Detect optimization patterns in code"""
        patterns = []
        lines = code.split("\n")

        # Detect list comprehension opportunities
        for i, line in enumerate(lines):
            if "for" in line and i + 1 < len(lines) and ".append(" in lines[i + 1]:
                patterns.append("list_comprehension_opportunity")

        # Detect ternary operator opportunities
        if re.search(r"if\s+.+:\s*return\s+.+\s*else:\s*return", code, re.MULTILINE):
            patterns.append("ternary_operator_opportunity")

        # Detect unnecessary temporary variables
        for line in lines:
            if re.match(r"\s*(temp_|tmp_|temporary_)\w+\s*=", line):
                patterns.append("unnecessary_temp_variable")

        # Detect string concatenation in loops
        if re.search(r"for\s+.+:\s*\w+\s*\+=\s*", code, re.MULTILINE):
            patterns.append("string_concat_in_loop")

        # Detect dict.get() opportunities
        if re.search(r"if\s+\w+\s+in\s+\w+:\s*\w+\[\w+\]", code):
            patterns.append("dict_get_opportunity")

        return patterns

    def suggest_changes(self, code: str) -> list[Change]:
        """Suggest specific optimization changes"""
        changes = []
        lines = code.split("\n")

        for i, line in enumerate(lines):
            # List comprehension opportunities
            if (
                "for" in line
                and i + 1 < len(lines)
                and ".append(" in lines[i + 1]
                and not line.strip().startswith("#")
            ):
                original_block = f"{line}\n{lines[i + 1]}"
                optimized = self._suggest_list_comprehension(line, lines[i + 1])

                if optimized != original_block:
                    changes.append(
                        Change(
                            agent_id=self.agent_id,
                            change_type=ChangeType.OPTIMIZATION,
                            original_code=original_block,
                            modified_code=optimized,
                            line_start=i,
                            line_end=i + 1,
                            confidence=0.7,
                            description="Convert to list comprehension",
                            impact_score=0.6,
                        )
                    )

            # Ternary operator opportunities
            if (
                re.search(r"if\s+.+:", line)
                and i + 2 < len(lines)
                and "return" in lines[i + 1]
                and "else:" in lines[i + 2]
            ):
                original_block = f"{line}\n{lines[i + 1]}\n{lines[i + 2]}\n{lines[i + 3] if i + 3 < len(lines) else ''}"
                ternary_result = self._suggest_ternary(
                    line,
                    lines[i + 1],
                    lines[i + 2],
                    lines[i + 3] if i + 3 < len(lines) else "",
                )

                if ternary_result:
                    changes.append(
                        Change(
                            agent_id=self.agent_id,
                            change_type=ChangeType.OPTIMIZATION,
                            original_code=original_block.strip(),
                            modified_code=ternary_result,
                            line_start=i,
                            line_end=i + 3,
                            confidence=0.8,
                            description="Convert to ternary operator",
                            impact_score=0.5,
                        )
                    )

            # String concatenation in loops
            if re.search(r"for\s+.+:", line) and i + 1 < len(lines):
                next_line = lines[i + 1]
                if re.search(r"\w+\s*\+=\s*", next_line):
                    changes.append(
                        Change(
                            agent_id=self.agent_id,
                            change_type=ChangeType.PERFORMANCE,
                            original_code=f"{line}\n{next_line}",
                            modified_code=f"# Consider using join() instead of string concatenation\n{line}\n{next_line}",
                            line_start=i,
                            line_end=i + 1,
                            confidence=0.6,
                            description="Use join() instead of string concatenation in loop",
                            impact_score=0.7,
                        )
                    )

            # Dict.get() opportunities
            if re.match(r"\s*if\s+(\w+)\s+in\s+(\w+):", line):
                match = re.match(r"\s*if\s+(\w+)\s+in\s+(\w+):", line)
                if match and i + 1 < len(lines):
                    key, dict_name = match.groups()
                    next_line = lines[i + 1]
                    if f"{dict_name}[{key}]" in next_line:
                        optimized = next_line.replace(
                            f"{dict_name}[{key}]", f"{dict_name}.get({key})"
                        )
                        changes.append(
                            Change(
                                agent_id=self.agent_id,
                                change_type=ChangeType.OPTIMIZATION,
                                original_code=f"{line}\n{next_line}",
                                modified_code=optimized,
                                line_start=i,
                                line_end=i + 1,
                                confidence=0.9,
                                description="Use dict.get() instead of key checking",
                                impact_score=0.4,
                            )
                        )

        return changes

    def validate_result(self, original: str, modified: str) -> bool:
        """Validate that changes improve code quality"""
        try:
            # Check syntax validity
            cst.parse_module(modified)

            # Check that we haven't just made cosmetic changes
            if original.strip() == modified.strip():
                return False

            # Check that the modification count is reasonable
            original_lines = len(original.split("\n"))
            modified_lines = len(modified.split("\n"))

            # Allow up to 20% change in line count
            return abs(modified_lines - original_lines) / max(original_lines, 1) <= 0.2

        except Exception:
            return False

    def vote(self, changes: list[Change]) -> dict[str, float]:
        """Vote on proposed changes from all agents"""
        votes = {}

        for change in changes:
            vote_key = (
                f"{change.agent_id}_{change.line_start}_{change.change_type.value}"
            )

            # Base vote on confidence
            base_vote = change.confidence

            # Boost optimization and performance changes
            if change.change_type == ChangeType.OPTIMIZATION:
                votes[vote_key] = min(base_vote * 1.2, 1.0)
            elif change.change_type == ChangeType.PERFORMANCE:
                votes[vote_key] = min(base_vote * 1.1, 1.0)
            elif change.change_type == ChangeType.SECURITY:
                # Slightly lower vote for security changes (not our specialty)
                votes[vote_key] = base_vote * 0.9
            else:
                votes[vote_key] = base_vote * 0.8

        return votes

    def get_priority(self) -> int:
        """Get agent priority for consensus"""
        return 7

    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold"""
        return 0.6

    def _suggest_list_comprehension(self, for_line: str, append_line: str) -> str:
        """Suggest list comprehension replacement"""
        # Extract loop variable and iterable
        for_match = re.search(r"for\s+(\w+)\s+in\s+(.+):", for_line)
        append_match = re.search(r"(\w+)\.append\((.+)\)", append_line.strip())

        if for_match and append_match:
            loop_var = for_match.group(1)
            iterable = for_match.group(2)
            list_name = append_match.group(1)
            append_expr = append_match.group(2)

            # Simple case: direct append of loop variable
            if append_expr.strip() == loop_var:
                return f"{list_name} = list({iterable})"
            else:
                return f"{list_name} = [{append_expr} for {loop_var} in {iterable}]"

        return f"{for_line}\n{append_line}"

    def _suggest_ternary(
        self, if_line: str, then_line: str, else_line: str, else_body: str
    ) -> Optional[str]:
        """Suggest ternary operator replacement"""
        if_match = re.search(r"if\s+(.+):", if_line)
        then_match = re.search(r"return\s+(.+)", then_line.strip())
        else_match = re.search(r"return\s+(.+)", else_body.strip())

        if if_match and then_match and else_match and "else:" in else_line:
            condition = if_match.group(1)
            then_value = then_match.group(1)
            else_value = else_match.group(1)

            return f"return {then_value} if {condition} else {else_value}"

        return None

    # _parse_code and _calculate_complexity inherited from BaseAgent
