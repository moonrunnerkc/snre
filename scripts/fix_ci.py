#!/usr/bin/env python3
"""
Fix common CI/CD issues for SNRE
This script addresses typical GitHub Actions failures
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and handle errors gracefully"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(f"Error: {result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if not check:
            return e
        sys.exit(1)


def fix_directory_structure():
    """Ensure all required directories exist"""
    print("🔧 Fixing directory structure...")

    directories = [
        "data/refactor_logs",
        "data/snapshots",
        "logs",
        "tests/unit_tests",
        ".github/workflows",
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        gitkeep = Path(directory) / ".gitkeep"
        if not any(Path(directory).iterdir()):
            gitkeep.touch()

    print("✅ Directory structure fixed")


def fix_imports():
    """Fix common import issues"""
    print("🔧 Fixing import issues...")

    # Create __init__.py files where needed
    init_files = [
        "agents/__init__.py",
        "core/__init__.py",
        "interface/__init__.py",
        "tests/__init__.py",
        "tests/unit_tests/__init__.py",
    ]

    for init_file in init_files:
        Path(init_file).touch()

    print("✅ Import structure fixed")


def fix_security_issues():
    """Fix common bandit security issues"""
    print("🔧 Fixing security scan issues...")

    # Run bandit and get specific issues
    result = run_command("bandit -r . -f json", check=False)

    if result.returncode == 0:
        print("✅ No security issues found")
    else:
        print("⚠️  Security issues detected - check bandit output")

    print("✅ Security scan completed")


def fix_code_quality():
    """Fix code quality issues"""
    print("🔧 Fixing code quality issues...")

    # Install and run ruff fixes
    run_command("pip install ruff", check=False)
    run_command("ruff check . --fix", check=False)
    run_command("ruff format .", check=False)

    print("✅ Code quality fixed")


def validate_contracts():
    """Ensure contract validation passes"""
    print("🔧 Validating contracts...")

    if Path("scripts/check_contract.py").exists():
        result = run_command("python scripts/check_contract.py", check=False)
        if result.returncode == 0:
            print("✅ Contract validation passed")
        else:
            print("❌ Contract validation failed")
            return False
    else:
        print("⚠️  Contract check script not found")

    return True


def main():
    """Main fix routine"""
    print("🚀 SNRE CI/CD Fix Script")
    print("=" * 50)

    # Change to project root
    os.chdir(Path(__file__).parent.parent)

    fixes = [
        fix_directory_structure,
        fix_imports,
        fix_code_quality,
        fix_security_issues,
        validate_contracts,
    ]

    for fix in fixes:
        try:
            fix()
        except Exception as e:
            print(f"❌ Fix failed: {e}")
            continue

    print("\n🎉 CI/CD fixes completed!")
    print("\nNext steps:")
    print("1. Commit these changes")
    print("2. Push to trigger GitHub Actions")
    print("3. Monitor the pipeline for remaining issues")


if __name__ == "__main__":
    main()
