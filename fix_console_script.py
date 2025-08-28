#!/usr/bin/env python3
"""
Fix the console script to point to snre_direct instead of main
"""

import os

console_script_path = "venv/bin/snre"

# Read current script
with open(console_script_path) as f:
    content = f.read()

print("Current console script content:")
print(content)
print("\n" + "="*50 + "\n")

# Fix the import
new_content = content.replace("from main import main", "from snre_direct import main")

# Write fixed script
with open(console_script_path, 'w') as f:
    f.write(new_content)

print("Fixed console script content:")
with open(console_script_path) as f:
    print(f.read())

# Make sure it's executable
os.chmod(console_script_path, 0o755)

print("\nConsole script fixed! Now try: snre start --path examples/sample_refactor.py --agents security_enforcer")
