#!/usr/bin/env python3
"""
Fix specific code quality issues identified by ruff
"""


def fix_refactored_py():
    """Fix the refactored.py import and redefinition issues"""
    try:
        with open("refactored.py") as f:
            content = f.read()

        lines = content.split("\n")

        # Remove duplicate import lines and fix the structure
        fixed_lines = []
        import_added = False

        for line in lines:
            if line.strip() == "import os" and not import_added:
                fixed_lines.append("import os")
                import_added = True
            elif line.strip() != "import os":  # Skip duplicate imports
                fixed_lines.append(line)

        # If no import was added, add it at the top
        if not import_added:
            fixed_lines.insert(0, "import os")

        with open("refactored.py", "w") as f:
            f.write("\n".join(fixed_lines))

        print("Fixed refactored.py import issues")

    except Exception as e:
        print(f"Error fixing refactored.py: {e}")


def fix_test_functional():
    """Fix bare except statements in test_functional.py"""
    try:
        with open("tests/unit_tests/test_functional.py") as f:
            content = f.read()

        # Replace bare except with except Exception
        fixed_content = content.replace("except:", "except Exception:")

        with open("tests/unit_tests/test_functional.py", "w") as f:
            f.write(fixed_content)

        print("Fixed test_functional.py bare except statements")

    except Exception as e:
        print(f"Error fixing test_functional.py: {e}")


def fix_test_working_components():
    """Fix unused variable in test_working_components.py"""
    try:
        with open("tests/unit_tests/test_working_components.py") as f:
            content = f.read()

        # Replace the unused variable line
        fixed_content = content.replace(
            "module = __import__(module_name, fromlist=[''])",
            "__import__(module_name, fromlist=[''])",
        )

        with open("tests/unit_tests/test_working_components.py", "w") as f:
            f.write(fixed_content)

        print("Fixed test_working_components.py unused variable")

    except Exception as e:
        print(f"Error fixing test_working_components.py: {e}")


if __name__ == "__main__":
    print("Fixing specific code quality issues...")
    fix_refactored_py()
    fix_test_functional()
    fix_test_working_components()
    print("Code quality fixes complete")
