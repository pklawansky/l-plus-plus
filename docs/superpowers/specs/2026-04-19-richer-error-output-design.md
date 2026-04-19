# Richer Error Output — Design Spec

**Date:** 2026-04-19  
**Status:** Approved

---

## Goal

Upgrade L++ compiler error messages from a minimal one-liner to a Rust-style diagnostic with a `-->` location pointer, a numbered source gutter, 2 context lines before the error, a caret annotation, and optional ANSI color — all with zero new dependencies.

---

## Output Format

For an error at `foo.lpp` line 5, col 12:

```
error: expected COLON, got EOF
 --> foo.lpp:5:12
  |
3 |   context_line_1
4 |   context_line_2
5 |   the_bad_line
  |              ^ expected COLON
```

Rules:
- Header: `error: <message>` (bold red when color enabled)
- Location line: ` --> <filename>:<line>:<col>` (bold cyan); omit `:<col>` if col is None; omit `<filename>:` prefix if filename is None; omit entire location line if line is None
- Gutter separator `  |` above and below the source block
- Up to 2 source lines before the error line (clamped at start of file); each prefixed with right-aligned line number and ` | `
- Error source line prefixed with its line number and ` | `
- Caret line: `  | <spaces>^` under the error column; if `err.expected` is set, append ` expected <value>` after `^`
- Omit entire source block (gutter + lines + caret) if `err.line` is None
- Omit caret line if `err.col` is None
- Gutter width = `len(str(error_line_number))`, minimum 2, so gutter is always at least `"  |"`

---

## Module Structure

### New: `src/lpp/errors.py`

Single public function:

```python
def format_error(
    label: str,
    err: Exception,
    source: str,
    filename: str | None = None,
    use_color: bool | None = None,
) -> str:
```

- `label`: the error kind prefix (always `"error"` in current usage; kept flexible for future `"warning"` use)
- `err`: any exception with optional `.line`, `.col`, `.expected` attributes
- `source`: full source text of the file
- `filename`: file path for the `-->` line; if None, omitted from location
- `use_color`: if None, defaults to `sys.stderr.isatty()`

Internal helpers (private):
- `_ansi(code: str, text: str, enabled: bool) -> str` — wraps text in ANSI escape if enabled, else returns text unchanged
- `_gutter_width(line_no: int) -> int` — returns `max(2, len(str(line_no)))`

ANSI codes used:
| Element | Code |
|---|---|
| `error:` label | bold red (`\033[1;31m`) |
| `-->` and line numbers | bold cyan (`\033[1;36m`) |
| `^` caret annotation | bold red (`\033[1;31m`) |
| Reset | `\033[0m` |

### Modified: `src/lpp/cli.py`

- Remove `_format_error` function entirely
- Add `from .errors import format_error`
- Update all four call sites to use `format_error`, passing `filename=src_path` where a path is available (single-file compile, check, watch, and dir modes)
- Single-file error call: `format_error("error", e, source, filename=args.file)`

---

## Testing

New file: `tests/test_errors.py`

| Test | What it checks |
|---|---|
| `test_plain_text_format` | Full multiline output matches expected string exactly (no color) |
| `test_color_codes_present` | `use_color=True` output contains `\033[` escape sequences |
| `test_two_context_lines` | Two lines before error line are shown in gutter |
| `test_context_clamped_at_start` | Only available lines shown when error is at line 1 or 2 |
| `test_caret_column_correct` | `^` appears under the right column |
| `test_no_caret_without_col` | Caret line absent when `col=None` |
| `test_no_snippet_without_line` | Source block absent when `line=None` |
| `test_gutter_width_single_digit` | Gutter uses 2-char width for line numbers < 10 |
| `test_gutter_width_multi_digit` | Gutter width expands for line numbers >= 10 |
| `test_expected_annotation` | `expected COLON` appended to caret when `err.expected` is set |
| `test_filename_in_location` | `filename` appears in `-->` line |
| `test_no_filename_in_location` | `-->` line shows without filename prefix when `filename=None` but `line` is set |

Existing `test_cli.py` integration: add one test confirming stderr output for a syntax error contains `-->` and a `^` character.

---

## What Does Not Change

- `LexError` and `ParseError` class signatures — no new fields needed
- `compile_lpp` public API
- All existing tests — only `_format_error` usages in `cli.py` are replaced
