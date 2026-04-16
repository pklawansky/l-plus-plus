#!/usr/bin/env python3
"""Validate that every L++ keyword and prelude alias is a single cl100k token.

Usage:
    pip install tiktoken
    python tools/validate_tokens.py
"""
import sys
import pathlib

# Ensure UTF-8 output on Windows consoles that default to cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import tiktoken
except ImportError:
    print("ERROR: tiktoken not installed. Run: pip install tiktoken")
    sys.exit(1)

# Add src/ to path so lpp imports work regardless of working directory
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from lpp.tokens import KEYWORDS
from lpp.prelude import PRELUDE

enc = tiktoken.get_encoding("cl100k_base")

def check(label: str, items: list[str]) -> int:
    """Check items, print results, return count of multi-token failures."""
    failures = 0
    print(f"\n=== {label} ===")
    for item in sorted(items):
        token_ids = enc.encode(item)
        if len(token_ids) == 1:
            print(f"  OK       {item!r:10}  id={token_ids[0]}")
        else:
            print(f"  MULTI    {item!r:10}  ids={token_ids}  ({len(token_ids)} tokens)")
            failures += 1
    return failures

total_failures = 0
total_failures += check("Keywords", list(KEYWORDS.keys()))
total_failures += check("Prelude aliases", list(PRELUDE.keys()))

print(f"\n{'=' * 40}")
if total_failures == 0:
    print("All items are single tokens. ✓")
else:
    print(f"{total_failures} item(s) are NOT single tokens — consider renaming.")
    sys.exit(1)
