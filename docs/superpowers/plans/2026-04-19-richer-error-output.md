# Richer Error Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `_format_error` in `cli.py` with a Rust-style diagnostic formatter in a dedicated `errors.py` module that shows a `-->` location pointer, a numbered source gutter, 2 context lines, a caret annotation, and optional ANSI color.

**Architecture:** New `src/lpp/errors.py` exports one public function `format_error(label, err, source, filename, use_color)`. `cli.py` drops `_format_error` and imports `format_error`, passing `filename=` at each call site. Zero new dependencies — color is plain ANSI escapes guarded by an `enabled` bool.

**Tech Stack:** Python 3.11+, pytest, ANSI escape codes (`\033[...m`)

---

## File Map

| Action | Path |
|---|---|
| Create | `src/lpp/errors.py` |
| Create | `tests/test_errors.py` |
| Modify | `src/lpp/cli.py` (lines 7–27, 48, 71, 101, 222) |
| Modify | `tests/test_cli.py` (add after line 119) |

---

### Task 1: Write all unit tests in `tests/test_errors.py` (expect all to fail)

**Files:**
- Create: `tests/test_errors.py`

- [ ] **Step 1: Write `tests/test_errors.py`**

```python
# tests/test_errors.py
import pytest
from lpp.errors import format_error


class FakeError(Exception):
    def __init__(self, msg, line=None, col=None, expected=None):
        super().__init__(msg)
        self.line = line
        self.col = col
        self.expected = expected


SOURCE = "first line\nsecond line\nthird line\nfourth line\nfifth line"


def test_plain_text_format():
    err = FakeError("expected COLON", line=4, col=8, expected="COLON")
    result = format_error("error", err, SOURCE, filename="foo.lpp", use_color=False)
    assert result == (
        "error: expected COLON\n"
        " --> foo.lpp:4:8\n"
        "   |\n"
        " 2 | second line\n"
        " 3 | third line\n"
        " 4 | fourth line\n"
        "   |        ^ expected COLON"
    )


def test_no_snippet_without_line():
    err = FakeError("something went wrong")
    result = format_error("error", err, SOURCE, use_color=False)
    assert result == "error: something went wrong"


def test_filename_in_location():
    err = FakeError("oops", line=2, col=1)
    result = format_error("error", err, SOURCE, filename="bar.lpp", use_color=False)
    assert " --> bar.lpp:2:1" in result


def test_no_filename_in_location():
    err = FakeError("oops", line=2, col=1)
    result = format_error("error", err, SOURCE, filename=None, use_color=False)
    assert " --> 2:1" in result
    assert "None" not in result


def test_two_context_lines():
    err = FakeError("bad", line=4, col=1)
    result = format_error("error", err, SOURCE, use_color=False)
    source_lines = [l for l in result.splitlines() if " | " in l]
    assert len(source_lines) == 3
    assert any("second line" in l for l in source_lines)
    assert any("third line" in l for l in source_lines)
    assert any("fourth line" in l for l in source_lines)


def test_context_clamped_at_start():
    err = FakeError("bad", line=1, col=1)
    result = format_error("error", err, SOURCE, use_color=False)
    source_lines = [l for l in result.splitlines() if " | " in l]
    assert len(source_lines) == 1
    assert "first line" in source_lines[0]


def test_caret_column_correct():
    # line=1 ("first line"), col=3 → ^ under the 3rd char
    err = FakeError("bad", line=1, col=3)
    result = format_error("error", err, SOURCE, use_color=False)
    caret_line = result.splitlines()[-1]
    # gw=2 → gp="   " (3 chars), pipe="|", space → 5 chars prefix before source content
    content_after_gutter = caret_line[5:]
    assert content_after_gutter == "  ^"  # 2 spaces (col-1) then ^


def test_no_caret_without_col():
    err = FakeError("bad", line=2)
    result = format_error("error", err, SOURCE, use_color=False)
    assert "^" not in result


def test_gutter_width_single_digit():
    # line <= 9 → gw=max(2,1)=2 → gp="   " (3 chars) → separator "   |"
    err = FakeError("bad", line=5, col=1)
    result = format_error("error", err, SOURCE, use_color=False)
    sep_line = result.splitlines()[2]
    assert sep_line == "   |"


def test_gutter_width_multi_digit():
    # line=100 → gw=max(2,3)=3 → gp="    " (4 chars) → separator "    |"
    long_source = "\n".join(f"line {i}" for i in range(1, 101))
    err = FakeError("bad", line=100, col=1)
    result = format_error("error", err, long_source, use_color=False)
    lines = result.splitlines()
    assert lines[2] == "    |"
    assert any("100 |" in l for l in lines)


def test_expected_annotation():
    err = FakeError("got INT", line=2, col=1, expected="COLON")
    result = format_error("error", err, SOURCE, use_color=False)
    assert "^ expected COLON" in result


def test_color_codes_present():
    err = FakeError("bad", line=2, col=1)
    result = format_error("error", err, SOURCE, use_color=True)
    assert "\033[" in result
```

- [ ] **Step 2: Run tests to confirm they all fail (module not yet created)**

```
pytest tests/test_errors.py -v
```

Expected: `ModuleNotFoundError: No module named 'lpp.errors'` or similar — all 12 tests fail.

---

### Task 2: Create `src/lpp/errors.py` and make all 12 tests pass

**Files:**
- Create: `src/lpp/errors.py`

- [x] **Step 3: Write `src/lpp/errors.py`**

```python
# src/lpp/errors.py
import sys


def _ansi(code: str, text: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def _gutter_width(line_no: int) -> int:
    return max(2, len(str(line_no)))


def format_error(
    label: str,
    err: Exception,
    source: str,
    filename: str | None = None,
    use_color: bool | None = None,
) -> str:
    if use_color is None:
        use_color = sys.stderr.isatty()

    line = getattr(err, "line", None)
    col = getattr(err, "col", None)
    expected = getattr(err, "expected", None)

    parts = [f"{_ansi('1;31', f'{label}:', use_color)} {err}"]

    if line is None:
        return parts[0]

    loc_parts = []
    if filename:
        loc_parts.append(filename)
    loc_parts.append(str(line))
    if col is not None:
        loc_parts.append(str(col))
    parts.append(f" {_ansi('1;36', '-->', use_color)} {':'.join(loc_parts)}")

    src_lines = source.splitlines()
    gw = _gutter_width(line)
    gp = " " * (gw + 1)
    pipe = _ansi("1;36", "|", use_color)

    parts.append(f"{gp}{pipe}")

    start = max(1, line - 2)
    for n in range(start, line + 1):
        if 0 < n <= len(src_lines):
            num = _ansi("1;36", str(n).rjust(gw), use_color)
            parts.append(f"{num} {pipe} {src_lines[n - 1]}")

    if col is not None:
        caret = _ansi("1;31", "^", use_color)
        annotation = f" expected {expected}" if expected else ""
        parts.append(f"{gp}{pipe} {' ' * (col - 1)}{caret}{annotation}")

    return "\n".join(parts)
```

- [x] **Step 4: Run tests to verify all 12 pass**

```
pytest tests/test_errors.py -v
```

Expected: 12 passed.

- [x] **Step 5: Commit**

```bash
git add src/lpp/errors.py tests/test_errors.py
git commit -m "feat(errors): add Rust-style diagnostic formatter with ANSI color"
```

---

### Task 3: Wire `format_error` into `cli.py`, replacing `_format_error`

**Files:**
- Modify: `src/lpp/cli.py` (lines 7–27, 48, 71, 101, 222)

- [x] **Step 6: Update `src/lpp/cli.py`**

Replace the import block at the top of `cli.py` — change:

```python
from .lexer import LexError
from .parser import ParseError
```

to:

```python
from .lexer import LexError
from .parser import ParseError
from .errors import format_error
```

Delete the entire `_format_error` function (lines 14–27):

```python
def _format_error(label: str, err: Exception, source: str) -> str:
    line = getattr(err, "line", None)
    col = getattr(err, "col", None)
    loc = f" at line {line}" if line else ""
    if col is not None:
        loc += f", col {col}"
    lines = [f"lpp: {label}{loc}: {err}"]
    if line and source:
        src_lines = source.splitlines()
        if 0 < line <= len(src_lines):
            lines.append(f"  {src_lines[line - 1]}")
            if col is not None:
                lines.append(f"  {' ' * (col - 1)}^")
    return "\n".join(lines)
```

Update the three call sites in `_check_dir`, `_compile_dir`, and `compile_one` (inside `_watch`). Each currently reads:

```python
print(_format_error(f"error in {src_path}", e, source), file=sys.stderr)
```

Change each to:

```python
print(format_error("error", e, source, filename=src_path), file=sys.stderr)
```

Update the single-file call site in `main()`. Currently:

```python
print(_format_error("error", e, source), file=sys.stderr)
```

Change to:

```python
print(format_error("error", e, source, filename=args.file), file=sys.stderr)
```

- [x] **Step 7: Run the full test suite to verify nothing broke**

```
pytest --tb=short -q
```

Expected: all existing tests pass (304+).
Result: 316 tests passed in 4.37s

- [x] **Step 8: Commit**

```bash
git add src/lpp/cli.py
git commit -m "refactor(cli): replace _format_error with format_error from errors module"
```
Commit: 2ce74fe

---

### Task 4: Add CLI integration test for the new format

**Files:**
- Modify: `tests/test_cli.py` (add after line 119)

- [ ] **Step 9: Add integration test to `tests/test_cli.py`**

Append the following function after the last test in the file:

```python
def test_syntax_error_has_rust_style_format():
    path = write_lpp("def\n")  # parse error — no function name
    try:
        code, out, err = lpp(path, "--check")
        assert code == 1
        assert "-->" in err
        assert "^" in err
    finally:
        os.unlink(path)
```

- [ ] **Step 10: Run the integration test to verify it passes**

```
pytest tests/test_cli.py::test_syntax_error_has_rust_style_format -v
```

Expected: PASSED.

- [ ] **Step 11: Run the full test suite one final time**

```
pytest --tb=short -q
```

Expected: all tests pass (316+: prior count + 12 new unit tests + 1 new integration test).

- [ ] **Step 12: Commit**

```bash
git add tests/test_cli.py
git commit -m "test(cli): verify Rust-style error format appears on stderr"
```
