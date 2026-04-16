# Tier 1: String Escape Re-encoding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the transpiler so that string literals containing `"`, `\`, `\n`, `\t`, or `\r` produce valid Python output instead of SyntaxErrors.

**Architecture:** The lexer correctly unescapes string content into semantic character values (e.g. `\"` → `"`). The transpiler must re-escape those values when emitting Python string syntax. The fix is a single static helper method `_escape_str_content` added to `Transpiler`, called from the existing `_string()` method.

**Tech Stack:** Python 3.11+, pytest

---

## File Structure

```
src/lpp/transpiler.py       # Add _escape_str_content(); update _string()
tests/test_transpiler.py    # Add 5 new string escape tests
docs/superpowers/specs/2026-04-13-lpp-language-design.md  # Fix isa/is, mark cl100k done
```

---

## Codebase Context

**`src/lpp/transpiler.py`** — The `Transpiler` class. The relevant method is `_string(self, parts: list) -> str` at line 188. It has two paths:

1. **Plain string** (no interpolation — all parts are `str`): joins parts and wraps in `"..."`.
2. **F-string** (has expression parts): builds an f-string, doubling `{` and `}` in literal parts.

Currently neither path escapes `"`, `\`, `\n`, `\t`, or `\r` before emitting. The fix adds `_escape_str_content` and calls it in both paths before the existing `{}`/`}}` handling.

**`tests/test_transpiler.py`** — Uses a `py(src)` helper that calls `compile_lpp(src)` and strips the prelude. All new tests follow this pattern: `py(lpp_source_string)` → compare to expected Python string.

Important: in Python test strings, a backslash must be doubled. So the L++ source `"path\\file"` (which contains the two-character sequence backslash-f-i-l-e) is written in the test as `'"path\\\\file"\n'`.

---

## Task 1: Fix string escape re-encoding in transpiler

**Files:**
- Modify: `src/lpp/transpiler.py:188-198`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_transpiler.py`:

```python
def test_string_with_double_quote():
    # L++ source: "say \"hi\""  →  Python: "say \"hi\""
    assert py('"say \\"hi\\""\n') == '"say \\"hi\\""'

def test_string_with_backslash():
    # L++ source: "path\\file"  →  Python: "path\\file"
    assert py('"path\\\\file"\n') == '"path\\\\file"'

def test_string_with_newline_escape():
    # L++ source: "line1\nline2"  →  Python: "line1\nline2"
    assert py('"line1\\nline2"\n') == '"line1\\nline2"'

def test_string_with_tab_escape():
    # L++ source: "col1\tcol2"  →  Python: "col1\tcol2"
    assert py('"col1\\tcol2"\n') == '"col1\\tcol2"'

def test_interpolated_string_with_double_quote():
    # L++ source: "$name$ said \"hi\""  →  Python: f"{name} said \"hi\""
    assert py('"$name$ said \\"hi\\""\n') == 'f"{name} said \\"hi\\""'
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_transpiler.py::test_string_with_double_quote tests/test_transpiler.py::test_string_with_backslash tests/test_transpiler.py::test_string_with_newline_escape tests/test_transpiler.py::test_string_with_tab_escape tests/test_transpiler.py::test_interpolated_string_with_double_quote -v
```

Expected: all 5 FAIL. The first four will produce mismatched strings; the last may raise a SyntaxError when the broken Python is validated.

- [ ] **Step 3: Add `_escape_str_content` and update `_string()` in `transpiler.py`**

Replace lines 188–198 (`_string` method) and add the new static method immediately after it:

```python
    def _string(self, parts: list) -> str:
        if all(isinstance(p, str) for p in parts):
            inner = self._escape_str_content("".join(parts))
            return f'"{inner}"'
        inner = ""
        for part in parts:
            if isinstance(part, str):
                escaped = self._escape_str_content(part)
                inner += escaped.replace("{", "{{").replace("}", "}}")
            else:
                inner += "{" + self._expr(part) + "}"
        return f'f"{inner}"'

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

- [ ] **Step 4: Run the new tests to verify they pass**

```
pytest tests/test_transpiler.py::test_string_with_double_quote tests/test_transpiler.py::test_string_with_backslash tests/test_transpiler.py::test_string_with_newline_escape tests/test_transpiler.py::test_string_with_tab_escape tests/test_transpiler.py::test_interpolated_string_with_double_quote -v
```

Expected: all 5 PASS.

- [ ] **Step 5: Run the full suite to check for regressions**

```
pytest -v
```

Expected: all existing tests still pass (the fix only adds escaping for characters that were previously unhandled — existing tests don't use `"`, `\`, `\n`, `\t`, or `\r` in string literals).

- [ ] **Step 6: Commit**

```bash
git add src/lpp/transpiler.py tests/test_transpiler.py
git commit -m "fix: re-escape string content in transpiler output"
```

---

## Task 2: Fix stale entries in the language design spec

**Files:**
- Modify: `docs/superpowers/specs/2026-04-13-lpp-language-design.md`

- [ ] **Step 1: Fix the prelude table entry for isinstance**

In `docs/superpowers/specs/2026-04-13-lpp-language-design.md`, find the prelude table row:

```
| `is` | isinstance |
```

Replace with:

```
| `isa` | isinstance |
```

Note: the implementation already uses `isa` (with a comment in `prelude.py` explaining that `is` is a Python keyword). The spec was simply never updated.

- [ ] **Step 2: Mark the cl100k validation open item as complete**

Find:

```
- [ ] Run every keyword and prelude alias through cl100k to confirm single-token status
```

Replace with:

```
- [x] Run every keyword and prelude alias through cl100k to confirm single-token status — all 50 pass (validated 2026-04-14, see `tools/validate_tokens.py`)
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-13-lpp-language-design.md
git commit -m "docs: fix isa prelude entry, mark cl100k validation complete"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Covered by |
|-----------------|-----------|
| Fix `"` in string output | Task 1 (`test_string_with_double_quote`) |
| Fix `\` in string output | Task 1 (`test_string_with_backslash`) |
| Fix `\n` in string output | Task 1 (`test_string_with_newline_escape`) |
| Fix `\t` in string output | Task 1 (`test_string_with_tab_escape`) |
| Fix `\r` — covered by `_escape_str_content` | Task 1 (no dedicated test — `\r` is rare, but the helper handles it) |
| Fix in f-string literal parts | Task 1 (`test_interpolated_string_with_double_quote`) |
| Update spec `is` → `isa` | Task 2 |
| Mark cl100k item done | Task 2 |

**Placeholder scan:** No TBDs, no vague steps, all code is complete.

**Type consistency:** `_escape_str_content` defined in Task 1 Step 3, used in same step. No cross-task type dependencies.
