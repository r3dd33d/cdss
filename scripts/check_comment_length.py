"""Fail if any inline comment exceeds 2 sentences (Constitution VII)."""
import re
import sys
from pathlib import Path

# Simple heuristic: count sentence-ending punctuation in a comment
SENTENCE_END = re.compile(r"[.!?]")
dirs = sys.argv[1:] or ["cdss", "app"]
violations = []

for d in dirs:
    for path in Path(d).rglob("*.py"):
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if "#" not in line:
                continue
            comment = line[line.index("#") + 1:].strip()
            if len(SENTENCE_END.findall(comment)) > 2:
                violations.append(f"{path}:{i}: {comment[:80]}")

if violations:
    print("COMMENT LENGTH VIOLATIONS (max 2 sentences):")
    print("\n".join(violations))
    sys.exit(1)
print("comment-length gate: PASS")
