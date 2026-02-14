"""
Security enforcement agent for SNRE
"""

import re

from agents.base_agent import BaseAgent
from snre.models.changes import AgentAnalysis
from snre.models.changes import Change
from snre.models.config import Config
from snre.models.enums import ChangeType


class SecurityEnforcer(BaseAgent):
    """Agent for enforcing security best practices"""

    def __init__(self, agent_id: str, config: Config):
        super().__init__(agent_id, config)

        # Security patterns to detect
        self.vulnerability_patterns = {
            "sql_injection": [
                r"cursor\.execute\([^)]*%[^)]*\)",
                r"\.format\([^)]*\).*execute",
                r'f".*{.*}.*".*execute',
                r"execute\([^)]*\+[^)]*\)",
            ],
            "command_injection": [
                r"os\.system\([^)]*\+",
                r"subprocess\.[^(]*\([^)]*\+",
                r"eval\([^)]*input",
                r"exec\([^)]*input",
            ],
            "path_traversal": [
                r"open\([^)]*\.\./.*\)",
                r'["\'][^"\']*\.\./[^"\']*["\']',
                r"os\.path\.join\([^)]*\.\.",
            ],
            "hardcoded_secrets": [
                r'password\s*=\s*["\'][^"\']{8,}["\']',
                r'api_key\s*=\s*["\'][A-Za-z0-9+/=]{16,}["\']',
                r'secret\s*=\s*["\'][^"\']{12,}["\']',
                r'token\s*=\s*["\'][A-Za-z0-9+/=]{20,}["\']',
            ],
            "weak_crypto": [
                r"hashlib\.md5\(",
                r"hashlib\.sha1\(",
                r"random\.random\(\)",
                r"ssl.*PROTOCOL_SSLv[23]",
            ],
            "unsafe_deserialization": [
                r"pickle\.loads\(",
                r"marshal\.loads\(",
                r"eval\([^)]*\)",
                r"exec\([^)]*\)",
            ],
        }

    def analyze(self, code: str) -> AgentAnalysis:
        """Analyze code for security vulnerabilities"""
        vulnerabilities = self.scan_vulnerabilities(code)
        complexity = (
            self._calculate_complexity(self._parse_code(code)) if code.strip() else 0.0
        )

        return AgentAnalysis(
            agent_id=self.agent_id,
            issues_found=len(vulnerabilities),
            complexity_score=complexity,
            security_risks=vulnerabilities,
            optimization_opportunities=[],
            confidence=0.9 if vulnerabilities else 0.7,
        )

    def suggest_changes(self, code: str) -> list[Change]:
        """Suggest security improvements"""
        changes = []
        lines = code.split("\n")

        for i, line in enumerate(lines):
            # SQL injection fixes
            if re.search(r"cursor\.execute\([^)]*%", line) and "?" not in line:
                original = line
                # Replace string formatting with parameterized queries
                fixed = re.sub(r"%s|%d|%\w+", "?", line)
                changes.append(
                    Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.SECURITY,
                        original_code=original,
                        modified_code=fixed,
                        line_start=i,
                        line_end=i,
                        confidence=0.9,
                        description="Replace string formatting with parameterized queries",
                        impact_score=0.9,
                    )
                )

            # Hardcoded password fixes
            if (
                re.search(r'password\s*=\s*["\'][^"\']{8,}["\']', line)
                and "os.environ" not in line
                and "getpass" not in line
            ):
                if match := re.search(r"(\w+)\s*=", line):
                    var_name = match.group(1)
                else:
                    var_name = "password"
                fixed = f'{var_name} = os.environ.get("PASSWORD")'
                changes.append(
                    Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.SECURITY,
                        original_code=line,
                        modified_code=fixed,
                        line_start=i,
                        line_end=i,
                        confidence=0.8,
                        description="Move hardcoded password to environment variable",
                        impact_score=0.8,
                    )
                )

            # API key fixes
            if (
                re.search(r'api_key\s*=\s*["\'][A-Za-z0-9+/=]{16,}["\']', line)
                and "os.environ" not in line
            ):
                if match := re.search(r"(\w+)\s*=", line):
                    var_name = match.group(1)
                else:
                    var_name = "api_key"
                fixed = f'{var_name} = os.environ.get("API_KEY")'
                changes.append(
                    Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.SECURITY,
                        original_code=line,
                        modified_code=fixed,
                        line_start=i,
                        line_end=i,
                        confidence=0.8,
                        description="Move hardcoded API key to environment variable",
                        impact_score=0.8,
                    )
                )

            # Dangerous eval/exec usage
            if ("eval(" in line or "exec(" in line) and (
                "input(" in line or "raw_input(" in line
            ):
                changes.append(
                    Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.SECURITY,
                        original_code=line,
                        modified_code="# SECURITY: eval()/exec() with user input removed - use ast.literal_eval() for safe evaluation",
                        line_start=i,
                        line_end=i,
                        confidence=0.95,
                        description="Remove dangerous eval()/exec() with user input",
                        impact_score=0.95,
                    )
                )

            # Weak cryptographic hashes
            if "hashlib.md5(" in line or "hashlib.sha1(" in line:
                fixed = line.replace("hashlib.md5(", "hashlib.sha256(").replace(
                    "hashlib.sha1(", "hashlib.sha256("
                )
                changes.append(
                    Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.SECURITY,
                        original_code=line,
                        modified_code=fixed,
                        line_start=i,
                        line_end=i,
                        confidence=0.8,
                        description="Replace weak hash algorithm with SHA-256",
                        impact_score=0.7,
                    )
                )

            # Path traversal vulnerabilities
            if re.search(r'["\'][^"\']*\.\./[^"\']*["\']', line):
                changes.append(
                    Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.SECURITY,
                        original_code=line,
                        modified_code=f"# SECURITY: Path traversal detected - validate and sanitize path\n{line}",
                        line_start=i,
                        line_end=i,
                        confidence=0.85,
                        description="Add path validation to prevent directory traversal",
                        impact_score=0.8,
                    )
                )

            # Unsafe random usage for security
            if "random.random(" in line and (
                "password" in line.lower()
                or "token" in line.lower()
                or "secret" in line.lower()
            ):
                fixed = line.replace(
                    "random.random()", "secrets.SystemRandom().random()"
                )
                changes.append(
                    Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.SECURITY,
                        original_code=line,
                        modified_code=fixed,
                        line_start=i,
                        line_end=i,
                        confidence=0.7,
                        description="Use cryptographically secure random for security purposes",
                        impact_score=0.6,
                    )
                )

            # Command injection fixes
            if re.search(r"os\.system\([^)]*\+", line):
                changes.append(
                    Change(
                        agent_id=self.agent_id,
                        change_type=ChangeType.SECURITY,
                        original_code=line,
                        modified_code="# SECURITY: Use subprocess with shell=False instead of os.system()",
                        line_start=i,
                        line_end=i,
                        confidence=0.9,
                        description="Replace os.system() with safer subprocess call",
                        impact_score=0.85,
                    )
                )

        return changes

    def vote(self, changes: list[Change]) -> dict[str, float]:
        """Vote on proposed changes with security priority"""
        votes = {}

        for change in changes:
            vote_key = (
                f"{change.agent_id}_{change.line_start}_{change.change_type.value}"
            )

            # Prioritize security changes highly
            if change.change_type == ChangeType.SECURITY:
                votes[vote_key] = min(change.confidence * 1.5, 1.0)
            elif change.change_type == ChangeType.OPTIMIZATION:
                # Support optimizations that don't compromise security
                if not self._compromises_security(change.modified_code):
                    votes[vote_key] = change.confidence * 0.9
                else:
                    votes[vote_key] = 0.1  # Veto insecure optimizations
            else:
                votes[vote_key] = change.confidence * 0.7

        return votes

    def validate_result(self, original: str, modified: str) -> bool:
        """Validate that changes don't introduce security issues"""
        # Check that no new vulnerabilities were introduced
        original_vulns = self.scan_vulnerabilities(original)
        modified_vulns = self.scan_vulnerabilities(modified)

        # Modified code should have fewer or equal vulnerabilities
        if len(modified_vulns) > len(original_vulns):
            return False

        # Check that critical patterns are addressed
        critical_patterns = ["eval(", "exec(", "os.system("]
        for pattern in critical_patterns:
            if pattern in original and pattern in modified:
                # Critical vulnerability not addressed
                return False

        return True

    def scan_vulnerabilities(self, code: str) -> list[str]:
        """Scan for security vulnerabilities"""
        vulnerabilities = []

        for vuln_type, patterns in self.vulnerability_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    vulnerabilities.extend([f"{vuln_type}:{pattern}" for _ in matches])

        return vulnerabilities

    def get_priority(self) -> int:
        """Get agent priority for consensus"""
        return 9

    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold"""
        return 0.8

    def _compromises_security(self, code: str) -> bool:
        """Check if code introduces security vulnerabilities"""
        dangerous_patterns = [
            r"eval\(",
            r"exec\(",
            r"os\.system\(",
            r"shell\s*=\s*True",
            r"pickle\.loads\(",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return True

        return False

    # _parse_code and _calculate_complexity inherited from BaseAgent
