"""
Loop simplification agent for SNRE
"""

import re

import libcst as cst

from agents.base_agent import BaseAgent
from snre.models.changes import AgentAnalysis
from snre.models.changes import Change
from snre.models.config import Config
from snre.models.enums import ChangeType


class LoopSimplifier(BaseAgent):
    """Agent for simplifying and optimizing loops"""

    def __init__(self, agent_id: str, config: Config):
        super().__init__(agent_id, config)

    def analyze(self, code: str) -> AgentAnalysis:
        """Analyze code for loop optimization opportunities"""
        try:
            tree = self._parse_code(code)
            loop_issues = self.detect_patterns(code)
            complexity = self._calculate_complexity(tree)

            return AgentAnalysis(
                agent_id=self.agent_id,
                issues_found=len(loop_issues),
                complexity_score=complexity,
                security_risks=[],
                optimization_opportunities=loop_issues,
                confidence=0.8 if loop_issues else 0.6,
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

    def suggest_changes(self, code: str) -> list[Change]:
        """Suggest loop optimizations"""
        return self.optimize_loops(code)

    def vote(self, changes: list[Change]) -> dict[str, float]:
        """Vote on proposed changes with loop focus"""
        votes = {}

        for change in changes:
            vote_key = (
                f"{change.agent_id}_{change.line_start}_{change.change_type.value}"
            )

            # High support for loop and performance optimizations
            if any(
                keyword in change.description.lower()
                for keyword in ["loop", "comprehension", "enumerate", "built-in"]
            ):
                votes[vote_key] = min(change.confidence * 1.3, 1.0)
            elif change.change_type == ChangeType.PERFORMANCE:
                votes[vote_key] = change.confidence * 1.1
            elif change.change_type == ChangeType.OPTIMIZATION:
                votes[vote_key] = change.confidence * 1.0
            else:
                votes[vote_key] = change.confidence * 0.6

        return votes

    def validate_result(self, original: str, modified: str) -> bool:
        """Validate that loop changes are correct"""
        try:
            # Ensure modified code is syntactically valid
            cst.parse_module(modified)

            # Check that loop count hasn't unreasonably increased
            original_loops = self._count_loops(original)
            modified_loops = self._count_loops(modified)

            # Allow small increases for refactoring, but not major increases
            return modified_loops <= original_loops * 1.2
        except Exception:
            return False

    def detect_patterns(self, code: str) -> list[str]:
        """Detect various loop inefficiency patterns"""
        issues = []

        # Range-len pattern
        if re.search(r"for\s+\w+\s+in\s+range\(len\(", code):
            issues.append("range_len_pattern")

        # Nested loops with append
        if re.search(r"for.*\n.*for.*\n.*\.append", code, re.MULTILINE):
            issues.append("nested_loop_with_append")

        # While True with break
        if re.search(r"while\s+True.*\n.*if.*break", code, re.MULTILINE | re.DOTALL):
            issues.append("infinite_loop_with_break")

        # Manual iteration when built-ins exist
        if re.search(r"for\s+\w+\s+in.*:\s*if\s+", code):
            issues.append("filter_opportunity")

        if re.search(r"for\s+\w+\s+in.*:\s*\w+\.append\(.*\w+.*\)", code):
            issues.append("map_opportunity")

        # Counting loops
        if re.search(r"count\s*=\s*0.*for.*count\s*\+=\s*1", code, re.DOTALL):
            issues.append("manual_counting")

        # Sum accumulation
        if re.search(r"sum\s*=\s*0.*for.*sum\s*\+=", code, re.DOTALL):
            issues.append("manual_sum")

        # Excessive nesting
        loop_count = code.count("for ") + code.count("while ")
        if loop_count > 3:
            issues.append("excessive_nested_loops")

        return issues

    def optimize_loops(self, code: str) -> list[Change]:
        """Find and optimize inefficient loops"""
        changes = []
        lines = code.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Range-len pattern
            if re.search(r"for\s+(\w+)\s+in\s+range\(len\((\w+)\)\)", line):
                match = re.search(r"for\s+(\w+)\s+in\s+range\(len\((\w+)\)\)", line)
                if match:
                    index_var, list_var = match.groups()
                    optimized = line.replace(
                        f"for {index_var} in range(len({list_var}))",
                        f"for {index_var}, item in enumerate({list_var})",
                    )
                    changes.append(
                        Change(
                            agent_id=self.agent_id,
                            change_type=ChangeType.OPTIMIZATION,
                            original_code=line,
                            modified_code=optimized,
                            line_start=i,
                            line_end=i,
                            confidence=0.9,
                            description="Replace range(len()) with enumerate()",
                            impact_score=0.6,
                        )
                    )

            # Simple filter pattern
            elif (
                re.search(r"for\s+(\w+)\s+in\s+(\w+):", line)
                and i + 1 < len(lines)
                and re.search(r"\s*if\s+", lines[i + 1])
            ):
                for_match = re.search(r"for\s+(\w+)\s+in\s+(\w+):", line)
                if_match = re.search(r"\s*if\s+(.+):", lines[i + 1])

                if for_match and if_match and i + 2 < len(lines):
                    var, iterable = for_match.groups()
                    condition = if_match.group(1)
                    body_line = lines[i + 2].strip()

                    if body_line.endswith(".append(" + var + ")"):
                        list_name = body_line.split(".append")[0].strip()
                        optimized = f"{list_name} = [item for item in {iterable} if {condition}]"

                        original_block = f"{line}\n{lines[i + 1]}\n{lines[i + 2]}"
                        changes.append(
                            Change(
                                agent_id=self.agent_id,
                                change_type=ChangeType.OPTIMIZATION,
                                original_code=original_block,
                                modified_code=optimized,
                                line_start=i,
                                line_end=i + 2,
                                confidence=0.8,
                                description="Convert filter loop to list comprehension",
                                impact_score=0.7,
                            )
                        )

            # Manual sum accumulation
            elif (
                re.search(r"(\w+)\s*=\s*0", line)
                and i + 1 < len(lines)
                and "for " in lines[i + 1]
            ):
                sum_match = re.search(r"(\w+)\s*=\s*0", line)
                for_match = re.search(r"for\s+(\w+)\s+in\s+(\w+):", lines[i + 1])

                if (
                    sum_match
                    and for_match
                    and i + 2 < len(lines)
                    and sum_match.group(1) + " +=" in lines[i + 2]
                ):
                    sum_var = sum_match.group(1)
                    loop_var, iterable = for_match.groups()

                    # Check if it's a simple sum
                    if lines[i + 2].strip() == f"{sum_var} += {loop_var}":
                        optimized = f"{sum_var} = sum({iterable})"
                        original_block = f"{line}\n{lines[i + 1]}\n{lines[i + 2]}"

                        changes.append(
                            Change(
                                agent_id=self.agent_id,
                                change_type=ChangeType.PERFORMANCE,
                                original_code=original_block,
                                modified_code=optimized,
                                line_start=i,
                                line_end=i + 2,
                                confidence=0.9,
                                description="Replace manual sum with built-in sum()",
                                impact_score=0.8,
                            )
                        )

            # While True with break pattern
            elif re.search(r"while\s+True:", line):
                block_end = self._find_while_block_end(lines, i)
                if block_end > i:
                    block = "\n".join(lines[i : block_end + 1])
                    if "break" in block:
                        changes.append(
                            Change(
                                agent_id=self.agent_id,
                                change_type=ChangeType.OPTIMIZATION,
                                original_code=block,
                                modified_code=f"# Consider refactoring infinite loop\n{block}",
                                line_start=i,
                                line_end=block_end,
                                confidence=0.6,
                                description="Consider refactoring while True loop",
                                impact_score=0.5,
                            )
                        )

            # Nested loop with simple append
            elif self._is_nested_loop_pattern(lines, i):
                block_end = self._find_nested_loop_end(lines, i)
                if block_end > i:
                    original_block = "\n".join(lines[i : block_end + 1])
                    optimized = self._optimize_nested_loop(original_block)

                    if optimized != original_block:
                        changes.append(
                            Change(
                                agent_id=self.agent_id,
                                change_type=ChangeType.PERFORMANCE,
                                original_code=original_block,
                                modified_code=optimized,
                                line_start=i,
                                line_end=block_end,
                                confidence=0.7,
                                description="Optimize nested loop structure",
                                impact_score=0.7,
                            )
                        )

            i += 1

        return changes

    def get_priority(self) -> int:
        """Get agent priority for consensus"""
        return 6

    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold"""
        return 0.7

    def _count_loops(self, code: str) -> int:
        """Count number of loops in code"""
        return code.count("for ") + code.count("while ")

    def _find_while_block_end(self, lines: list[str], start_idx: int) -> int:
        """Find the end of a while block"""
        if start_idx >= len(lines):
            return start_idx

        base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())

        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                continue

            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and line.strip():
                return i - 1

        return len(lines) - 1

    def _is_nested_loop_pattern(self, lines: list[str], start_idx: int) -> bool:
        """Check if lines starting at start_idx contain nested loop pattern"""
        if start_idx >= len(lines) - 2:
            return False

        first_line = lines[start_idx].strip()
        if not first_line.startswith("for "):
            return False

        # Look for nested for loop in next few lines
        base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())

        for i in range(start_idx + 1, min(start_idx + 10, len(lines))):
            line = lines[i]
            if line.strip() and "for " in line:
                current_indent = len(line) - len(line.lstrip())
                if current_indent > base_indent:
                    # Check if there's an append in the next few lines
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if ".append(" in lines[j]:
                            return True

        return False

    def _find_nested_loop_end(self, lines: list[str], start_idx: int) -> int:
        """Find the end of a nested loop structure"""
        if start_idx >= len(lines):
            return start_idx

        base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())

        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                continue

            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and line.strip():
                return i - 1

        return len(lines) - 1

    def _optimize_nested_loop(self, loop_block: str) -> str:
        """Attempt to optimize nested loop structure"""
        lines = loop_block.split("\n")

        # Simple pattern: nested loops with append
        if len(lines) >= 3 and ".append(" in loop_block:
            # Find the outer and inner loop variables
            outer_match = re.search(r"for\s+(\w+)\s+in\s+(\w+):", lines[0])
            if outer_match:
                outer_var, outer_iter = outer_match.groups()

                # Look for inner loop
                for i in range(1, len(lines)):
                    inner_match = re.search(r"for\s+(\w+)\s+in\s+(\w+):", lines[i])
                    if inner_match:
                        inner_var, inner_iter = inner_match.groups()

                        # Look for append
                        for j in range(i + 1, len(lines)):
                            if ".append(" in lines[j]:
                                append_match = re.search(
                                    r"(\w+)\.append\((.+)\)", lines[j]
                                )
                                if append_match:
                                    list_name, append_expr = append_match.groups()

                                    # Suggest nested comprehension
                                    suggestion = f"{list_name} = [{append_expr} for {outer_var} in {outer_iter} for {inner_var} in {inner_iter}]"
                                    return f"# Consider nested comprehension:\n# {suggestion}\n{loop_block}"

        return loop_block

    # _parse_code and _calculate_complexity inherited from BaseAgent
