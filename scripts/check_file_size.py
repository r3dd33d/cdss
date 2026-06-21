"""Fail if any .py file exceeds 400 lines (Constitution I)."""
import sys
from pathlib import Path

HARD_LIMIT = 400
dirs = sys.argv[1:] or ["cdss", "app"]
violations = []

for d in dirs:
    for path in Path(d).rglob("*.py"):
        lines = path.read_text().count("\n")
        if lines > HARD_LIMIT:
            violations.append(f"{path}: {lines} lines (limit {HARD_LIMIT})")

if violations:
    print("FILE SIZE VIOLATIONS:")
    print("\n".join(violations))
    sys.exit(1)
print("file-size gate: PASS")
