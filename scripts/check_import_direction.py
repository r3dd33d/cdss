"""Fail if cdss/ imports streamlit (Constitution II)."""
import re
import sys
from pathlib import Path

dirs = sys.argv[1:] or ["cdss"]
pattern = re.compile(r"^\s*(import streamlit|from streamlit)")
violations = []

for d in dirs:
    for path in Path(d).rglob("*.py"):
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if pattern.match(line):
                violations.append(f"{path}:{i}: {line.strip()}")

if violations:
    print("IMPORT DIRECTION VIOLATIONS (cdss must not import streamlit):")
    print("\n".join(violations))
    sys.exit(1)
print("import-direction gate: PASS")
