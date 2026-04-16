# Tier 1: String Escape Re-encoding Fix

**Date:** 2026-04-16
**Status:** Approved

---

## Goal

Fix a transpiler bug where string literals containing `"`, `\`, `\n`, `\t`, or `\r` produce invalid or incorrect Python output.

---

## Problem

The lexer correctly converts escape sequences to their semantic character values when tokenizing string literals:

| L++ source | Lexed value |
|-----------|-------------|
| `\"` | `"` (double-quote char) |
| `\\` | `\` (backslash char) |
| `\n` | newline char (0x0A) |
| `\t` | tab char (0x09) |

These semantic values are stored in `StringLiteral.parts` as actual characters. The transpiler's `_string()` method then emits them directly into Python string delimiters without re-escaping, producing broken Python:

```
L++ source:    "say \"hi\""
Python output: "say "hi""        ← SyntaxError
```

```
L++ source:    "line1\nline2"
Python output: "line1
line2"                            ← SyntaxError
```

---

## Design

### What changes

**`src/lpp/transpiler.py` — `Transpiler._string()`**

Add a static helper method:

```python
@staticmethod
def _escape_str_content(s: str) -> str:
    return (s
        .replace("\\", "\\\\")   # must be first — avoids double-escaping
        .replace('"',  '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )
```

Apply it in `_string()` on every literal string part before emitting:

- **Plain string path** (no interpolation): escape the joined content before wrapping in `"..."`.
- **F-string path** (has interpolation): escape each literal part first, then apply the existing `{` → `{{` / `}` → `}}` substitution. Order matters: backslash escaping must precede brace doubling.

**`tests/test_transpiler.py`**

Add tests covering:
- `"` inside a string
- `\` inside a string
- `\n` inside a string (newline)
- `\t` inside a string (tab)
- `"` inside an interpolated string (f-string literal part)

**`docs/superpowers/specs/2026-04-13-lpp-language-design.md`**

Correct two stale entries:
- Prelude table: `| is | isinstance |` → `| isa | isinstance |`
- Open items: mark the cl100k tokenizer validation item as complete (all 50 keywords/aliases confirmed single-token in a prior session)

### What does NOT change

- Lexer — escape sequence unescaping is correct; AST stores semantic values
- Parser — no changes
- AST nodes — `StringLiteral.parts` correctly stores actual character values
- Escape sequences beyond the five listed (`\0`, `\x`, `\u`, `\U`, `\N`) are Tier 5

---

## Test cases

| L++ source | Expected Python output |
|-----------|----------------------|
| `"say \"hi\""` | `"say \"hi\""` |
| `"path\\file"` | `"path\\file"` |
| `"line1\nline2"` | `"line1\nline2"` |
| `"col1\tcol2"` | `"col1\tcol2"` |
| `"$name$ said \"hi\""` | `f"{name} said \"hi\""` |

---

## Out of scope

- Extended escape sequences (`\x`, `\u`, `\U`, `\N{...}`, `\0`) — Tier 5
- Raw string literals `r"..."` — Tier 5
- Byte string literals `b"..."` — Tier 5
