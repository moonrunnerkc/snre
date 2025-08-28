"""
Security enforcement agent for SNRE
"""

import re

from agents.base_agent import BaseAgent
from contracts import AgentAnalysis, Change, ChangeType, Config


class SecurityEnforcer(BaseAgent):
    """Agent for enforcing security best practices"""

    def __init__(self, agent_id: str, config: Config):
        super().__init__(agent_id, config)
        self._priority = 9
        self._confidence_threshold = 0.8

        # Security patterns to detect
        self.vulnerability_patterns = {
            'sql_injection': [
                r'cursor\.execute\([^)]*%[^)]*\)',
                r'\.format\([^)]*\).*execute',
                r'f".*{.*}.*".*execute'
            ],
            'command_injection': [
                r'os\.system\([^)]*\+',
                r'subprocess\.[^(]*\([^)]*\+',
                r'eval\([^)]*input'
            ],
            'path_traversal': [
                r'open\([^)]*\.\./.*\)',
                r'\.\./',
                r'os\.path\.join\([^)]*\.\.'
            ],
            'hardcoded_secrets': [
                r'password\s*=\s*["\'][^"\']*["\']',
                r'api_key\s*=\s*["\'][^"\']*["\']',
                r'secret\s*=\s*["\'][^"\']*["\']'
            ]
        }

    def analyze(self, code: str) -> AgentAnalysis:
        """Analyze code for security vulnerabilities"""
        vulnerabilities = self.scan_vulnerabilities(code)
        complexity = self._calculate_complexity(self._parse_code(code)) if code.strip() else 0.0

        return AgentAnalysis(
            agent_id=self.agent_id,
            issues_found=len(vulnerabilities),
            complexity_score=complexity,
            security_risks=vulnerabilities,
            optimization_opportunities=[],
            confidence=0.9
        )

    def suggest_changes(self, code: str) -> list[Change]:
        """Suggest security improvements"""
        changes = []
        lines = code.split('\n')

        for i, line in enumerate(lines):
            # Check for SQL injection patterns - only if not already fixed
            if re.search(r'cursor\.execute\([^)]*%', line) and '?' not in line:
                change = Change(
                    agent_id=self.agent_id,
                    change_type=ChangeType.SECURITY,
                    original_code=line,
                    modified_code=line.replace('%s', '?').replace('%d', '?'),
                    line_start=i,
                    line_end=i,
                    confidence=0.9,
                    description="Replace string formatting with parameterized queries",
                    impact_score=0.9
                )
                changes.append(change)

            # Check for hardcoded passwords - only if not already using env vars
            if re.search(r'password\s*=\s*["\'][^"\']+["\']', line) and 'os.environ' not in line:
                change = Change(
                    agent_id=self.agent_id,
                    change_type=ChangeType.SECURITY,
                    original_code=line,
                    modified_code=line.split('=')[0] + '= os.environ.get("PASSWORD")',
                    line_start=i,
                    line_end=i,
                    confidence=0.8,
                    description="Move hardcoded password to environment variable",
                    impact_score=0.8
                )
                changes.append(change)

            # Check for api_key hardcoding - only if not already using env vars
            if re.search(r'api_key\s*=\s*["\'][^"\']+["\']', line) and 'os.environ' not in line:
                change = Change(
                    agent_id=self.agent_id,
                    change_type=ChangeType.SECURITY,
                    original_code=line,
                    modified_code=line.split('=')[0] + '= os.environ.get("API_KEY")',
                    line_start=i,
                    line_end=i,
                    confidence=0.8,
                    description="Move hardcoded API key to environment variable",
                    impact_score=0.8
                )
                changes.append(change)

            # Check for eval usage - only if eval is still present
            if 'eval(' in line and 'input(' in line and '# SECURITY:' not in line:
                change = Change(
                    agent_id=self.agent_id,
                    change_type=ChangeType.SECURITY,
                    original_code=line,
                    modified_code="# SECURITY: eval() with user input removed",
                    line_start=i,
                    line_end=i,
                    confidence=0.95,
                    description="Remove dangerous eval() with user input",
                    impact_score=0.95
                )
                changes.append(change)

        return changes

    def vote(self, changes: list[Change]) -> dict[str, float]:
        """Vote on proposed changes with security priority"""
        votes = {}

        for change in changes:
            vote_key = f"{change.agent_id}_{change.line_start}_{change.change_type.value}"

            # Prioritize security changes highly
            if change.change_type == ChangeType.SECURITY:
                votes[vote_key] = min(change.confidence * 1.5, 1.0)
            elif change.change_type == ChangeType.OPTIMIZATION:
                # Support optimizations that don't compromise security
                votes[vote_key] = change.confidence * 0.9
            else:
                votes[vote_key] = change.confidence * 0.7

        return votes

    def validate_result(self, original: str, modified: str) -> bool:
        """Validate that changes don't introduce security issues"""
        # Check that no new vulnerabilities were introduced
        original_vulns = self.scan_vulnerabilities(original)
        modified_vulns = self.scan_vulnerabilities(modified)

        # Modified code should have fewer or equal vulnerabilities
        return len(modified_vulns) <= len(original_vulns)

    def get_priority(self) -> int:
        """Get agent priority for consensus"""
        return self._priority

    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold"""
        return self._confidence_threshold

    def scan_vulnerabilities(self, code: str) -> list[str]:
        """Scan for security vulnerabilities"""
        vulnerabilities = []

        for vuln_type, patterns in self.vulnerability_patterns.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    vulnerabilities.append(f"{vuln_type}: {pattern}")

        return vulnerabilities
