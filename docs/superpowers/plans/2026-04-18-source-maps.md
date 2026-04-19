# Source Maps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thread L++ source line numbers through the AST so that runtime tracebacks in `--run` mode point to `.lpp` lines instead of generated Python lines.

**Architecture:** Three-layer approach: (1) each Statement AST node gains a `line: int | None = None` field; (2) the parser captures `self.peek().line` before dispatching each statement and stores it on the returned node; (3) the transpiler appends a `  # lpp:N` trailing comment to the first output line of each statement; and (4) `cli.py`'s `--run` branch scans those markers to build a `{py_line → lpp_line}` map, installs a `sys.excepthook` before `exec()`, and the hook rewrites the traceback to show `.lpp` file and line.

**Tech Stack:** Python 3.11, stdlib only (`re`, `sys`, `traceback`).

---

## File Structure

| File | Change |
|------|--------|
| `src/lpp/ast_nodes.py` | Add `line: int \| None = None` as final field on all 24 Statement dataclasses |
| `src/lpp/parser.py` | Rename `_parse_statement` → `_parse_statement_body`; new `_parse_statement` captures line, calls body, annotates result |
| `src/lpp/transpiler.py` | Rename `_stmt` → `_emit_stmt`; new `_stmt` calls `_emit_stmt` then injects `  # lpp:N` on the first output line |
| `src/lpp/cli.py` | Add `_build_line_map(python_src)` helper; add `_install_run_hook(lpp_path, lpp_src, line_map)` helper; call both in the `--run` branch |
| `tests/test_parser.py` | Add 2 tests: statement nodes carry `.line`; second statement has correct line |
| `tests/test_transpiler.py` | Add 3 tests: marker present, correct line, multi-statement |
| `tests/test_cli.py` | Add 1 test: `--run` traceback names `.lpp` file and correct line |

---

## Task 1: Add `line` field to Statement nodes

**Files:**
- Modify: `src/lpp/ast_nodes.py`
- Test: `tests/test_parser.py`

The current Statement dataclasses have no `line` field. We add `line: int | None = None` as the last field of every class that appears in the `Statement` union. Putting it last means no existing call sites break (all positional args still work).

- [ ] **Step 1: Write the failing test**

Add at the bottom of `tests/test_parser.py`:

```python
def test_statement_carries_line():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("x = 1\n").tokenize()
    prog = Parser(tokens).parse()
    assert hasattr(prog.body[0], "line"), "Statement node has no .line attribute"
    assert prog.body[0].line == 1

def test_second_statement_has_correct_line():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("x = 1\ny = 2\n").tokenize()
    prog = Parser(tokens).parse()
    assert prog.body[0].line == 1
    assert prog.body[1].line == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_parser.py::test_statement_carries_line tests/test_parser.py::test_second_statement_has_correct_line -v
```

Expected: FAIL — `Assignment` has no `.line` attribute.

- [ ] **Step 3: Add `line` field to all 24 Statement node classes in `ast_nodes.py`**

For each class listed below, add `line: int | None = None` as the **last field** (after any existing default-valued fields):

```python
@dataclass
class FunctionDef:
    name: str
    params: list["Param"]
    body: list[Statement]
    is_method: bool
    decorators: list = field(default_factory=list)
    line: int | None = None

@dataclass
class ClassDef:
    name: str
    bases: list[str]
    body: list[FunctionDef]
    decorators: list = field(default_factory=list)
    line: int | None = None

@dataclass
class Assignment:
    target: str | Expression
    value: Expression
    line: int | None = None

@dataclass
class AugAssignment:
    target: str | Expression
    op: str
    value: Expression
    line: int | None = None

@dataclass
class AppendStatement:
    target: Expression
    value: Expression
    line: int | None = None

@dataclass
class IfStatement:
    condition: Expression
    body: list[Statement]
    elifs: list[tuple[Expression | None, list[Statement]]] = field(default_factory=list)
    line: int | None = None

@dataclass
class ForStatement:
    targets: list[str]
    iterable: Expression
    body: list[Statement]
    else_body: list[Statement] | None = None
    line: int | None = None

@dataclass
class DoStatement:
    condition: Expression
    body: list[Statement]
    else_body: list[Statement] | None = None
    line: int | None = None

@dataclass
class TryStatement:
    body: list[Statement]
    handlers: list["ErrHandler"]
    finally_body: list[Statement] | None = None
    line: int | None = None

@dataclass
class RetStatement:
    value: Expression | None
    line: int | None = None

@dataclass
class UseStatement:
    imports: list["UseImport"]
    line: int | None = None

@dataclass
class AliasStatement:
    name: str
    target: Expression
    line: int | None = None

@dataclass
class ExprStatement:
    expr: Expression
    line: int | None = None

@dataclass
class BreakStatement:
    line: int | None = None

@dataclass
class ContinueStatement:
    line: int | None = None

@dataclass
class RaiseStatement:
    exc: Expression | None = None
    cause: Expression | None = None
    line: int | None = None

@dataclass
class WithStatement:
    items: list[tuple[Expression, str | None]]
    body: list[Statement]
    line: int | None = None

@dataclass
class GlobalStatement:
    names: list[str]
    line: int | None = None

@dataclass
class NonlocalStatement:
    names: list[str]
    line: int | None = None

@dataclass
class UnpackAssignment:
    targets: list[Expression]
    value: Expression
    line: int | None = None

@dataclass
class AssertStatement:
    test: Expression
    msg: Expression | None = None
    line: int | None = None

@dataclass
class DelStatement:
    targets: list[Expression]
    line: int | None = None

@dataclass
class PassStatement:
    line: int | None = None

@dataclass
class YieldStatement:
    value: "Expression | None" = None
    is_from: bool = False
    line: int | None = None
```

**Note on `RetStatement`:** The current definition is `RetStatement(value: Expression | None)` — no default. After adding `line`, it becomes `RetStatement(value, line=None)`. Existing calls `RetStatement(expr)` still work.

**Note on `BreakStatement` / `ContinueStatement` / `PassStatement`:** These currently have `pass` as the class body. Replace `pass` with the `line` field.

- [ ] **Step 4: Update the parser to attach line numbers**

In `parser.py`, rename `_parse_statement` → `_parse_statement_body` and add a new wrapper:

```python
def _parse_statement(self) -> Statement:
    stmt_line = self.peek().line
    node = self._parse_statement_body()
    node.line = stmt_line
    return node

def _parse_statement_body(self) -> Statement:
    tt = self.peek_type()

    if tt == TokenType.AT and self._is_decorator_context():
        decorators = self._collect_decorators()
        if self.peek_type() == TokenType.DEF:
            return self._parse_function(decorators)
        return self._parse_class(decorators)

    if tt == TokenType.DEF:
        return self._parse_function()
    if tt == TokenType.CLASS:
        return self._parse_class()
    if tt == TokenType.IF:
        return self._parse_if()
    if tt == TokenType.FOR:
        return self._parse_for()
    if tt == TokenType.WHILE:
        return self._parse_while()
    if tt == TokenType.TRY:
        return self._parse_try()
    if tt == TokenType.RETURN:
        return self._parse_return()
    if tt == TokenType.USE:
        return self._parse_use()
    if tt == TokenType.ALIAS:
        return self._parse_alias()
    if tt == TokenType.BREAK:    return self._parse_break()
    if tt == TokenType.CONTINUE: return self._parse_continue()
    if tt == TokenType.GLOBAL:   return self._parse_global()
    if tt == TokenType.NL:       return self._parse_nonlocal()
    if tt == TokenType.RAISE:    return self._parse_raise()
    if tt == TokenType.WITH:     return self._parse_with()
    if tt == TokenType.ASSERT:   return self._parse_assert()
    if tt == TokenType.DEL:      return self._parse_del()
    if tt == TokenType.PASS:     return self._parse_pass()
    if tt == TokenType.YIELD:    return self._parse_yield()

    return self._parse_expr_or_assign()
```

**This is the complete body of `_parse_statement_body`.** It is identical to the current `_parse_statement`.

- [ ] **Step 5: Run the new tests and full suite**

```
pytest tests/test_parser.py::test_statement_carries_line tests/test_parser.py::test_second_statement_has_correct_line -v
pytest -q
```

Expected: both new tests PASS; full suite still passes (295 tests).

- [ ] **Step 6: Commit**

```bash
git add src/lpp/ast_nodes.py src/lpp/parser.py tests/test_parser.py
git commit -m "feat(ast): add line field to Statement nodes; parser records source lines"
```

---

## Task 2: Transpiler emits `# lpp:N` markers

**Files:**
- Modify: `src/lpp/transpiler.py`
- Test: `tests/test_transpiler.py`

The transpiler's `_stmt()` is the single exit point for all statement output. We rename it to `_emit_stmt()` and add a thin `_stmt()` wrapper that appends `  # lpp:N` to the first line of the returned string when line info is available.

- [ ] **Step 1: Write the failing tests**

Add at the bottom of `tests/test_transpiler.py`:

```python
def test_lpp_marker_emitted():
    out = compile_lpp("x = 1\n")
    assert "# lpp:1" in out

def test_lpp_markers_on_correct_lines():
    out = compile_lpp("x = 1\ny = 2\n")
    x_annotated = next(l for l in out.splitlines() if "x = 1" in l)
    y_annotated = next(l for l in out.splitlines() if "y = 2" in l)
    assert "# lpp:1" in x_annotated
    assert "# lpp:2" in y_annotated

def test_lpp_marker_on_compound_statement():
    out = compile_lpp("if True\n  x = 1\n")
    if_line = next(l for l in out.splitlines() if l.strip().startswith("if True"))
    assert "# lpp:1" in if_line
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_transpiler.py::test_lpp_marker_emitted tests/test_transpiler.py::test_lpp_markers_on_correct_lines tests/test_transpiler.py::test_lpp_marker_on_compound_statement -v
```

Expected: FAIL — no `# lpp:N` markers in output yet.

- [ ] **Step 3: Add the `_stmt` wrapper in `transpiler.py`**

Rename the current `_stmt` method to `_emit_stmt`. Then add:

```python
def _stmt(self, node: Statement, depth: int) -> str:
    result = self._emit_stmt(node, depth)
    lpp_line = getattr(node, "line", None)
    if lpp_line is not None:
        first, sep, rest = result.partition("\n")
        return f"{first}  # lpp:{lpp_line}{sep}{rest}"
    return result
```

The `_emit_stmt` method body is identical to the former `_stmt` — no other changes.

**Note:** `getattr(node, "line", None)` is used instead of `node.line` so the transpiler still works if called with a node that predates this change (e.g., hand-constructed in tests).

- [ ] **Step 4: Run the new tests and full suite**

```
pytest tests/test_transpiler.py::test_lpp_marker_emitted tests/test_transpiler.py::test_lpp_markers_on_correct_lines tests/test_transpiler.py::test_lpp_marker_on_compound_statement -v
pytest -q
```

Expected: all 3 new tests PASS; full suite still passes (297 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lpp/transpiler.py tests/test_transpiler.py
git commit -m "feat(transpiler): emit # lpp:N line markers on each statement"
```

---

## Task 3: `--run` installs a traceback rewriting hook

**Files:**
- Modify: `src/lpp/cli.py`
- Test: `tests/test_cli.py`

When `lpp file.lpp --run` executes and the user's code raises an unhandled exception, Python's default traceback shows Python line numbers in the generated code. We install a `sys.excepthook` before `exec()` that remaps those line numbers to L++ lines using the `# lpp:N` markers baked into the generated source.

The hook also shows the raw L++ source line (read from the original `.lpp` file) instead of the generated Python line.

- [ ] **Step 1: Write the failing test**

Add at the bottom of `tests/test_cli.py`:

```python
def test_run_traceback_remaps_to_lpp_line():
    # Line 1: valid assignment; line 2: raises
    path = write_lpp("x = 1\nraise ValueError('oops')\n")
    try:
        code, out, err = lpp(path, "--run")
        assert code != 0
        assert os.path.basename(path) in err or path in err
        assert "line 2" in err
        assert "ValueError" in err
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_cli.py::test_run_traceback_remaps_to_lpp_line -v
```

Expected: FAIL — current traceback shows Python line numbers, not `line 2`.

- [ ] **Step 3: Add helpers to `cli.py`**

Add the following two functions after the `_watch` function (before `main`):

```python
def _build_line_map(python_src: str) -> dict[int, int]:
    """Return {py_lineno: lpp_lineno} by scanning # lpp:N markers.

    Lines between markers inherit the nearest preceding marker's lpp line.
    """
    import re
    result: dict[int, int] = {}
    current: int | None = None
    for py_lineno, src_line in enumerate(python_src.splitlines(), 1):
        m = re.search(r"# lpp:(\d+)", src_line)
        if m:
            current = int(m.group(1))
        if current is not None:
            result[py_lineno] = current
    return result


def _install_run_hook(lpp_path: str, lpp_src: str, line_map: dict[int, int]) -> None:
    """Replace sys.excepthook with one that remaps tracebacks to .lpp lines."""
    import traceback as tb_mod
    lpp_lines = lpp_src.splitlines()

    def hook(exc_type, exc_value, exc_tb):
        frames = tb_mod.extract_tb(exc_tb)
        sys.stderr.write("Traceback (most recent call last):\n")
        for frame in frames:
            if frame.filename == lpp_path:
                lpp_lineno = line_map.get(frame.lineno, frame.lineno)
                sys.stderr.write(f'  File "{lpp_path}", line {lpp_lineno}\n')
                if 0 < lpp_lineno <= len(lpp_lines):
                    sys.stderr.write(f"    {lpp_lines[lpp_lineno - 1].strip()}\n")
            else:
                sys.stderr.write(
                    f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}\n'
                )
                if frame.line:
                    sys.stderr.write(f"    {frame.line}\n")
        sys.stderr.write(f"{exc_type.__name__}: {exc_value}\n")

    sys.excepthook = hook
```

- [ ] **Step 4: Wire up the hook in `main()`**

Locate the `--run` branch in `main()` (currently `elif args.run:`). Replace it with:

```python
elif args.run:
    line_map = _build_line_map(python_src)
    _install_run_hook(args.file, source, line_map)
    exec(compile(python_src, args.file, "exec"), {"__name__": "__main__"})
```

`source` is the raw L++ source already read earlier in `main()` (`with open(args.file) as f: source = f.read()`).

- [ ] **Step 5: Run the new test and full suite**

```
pytest tests/test_cli.py::test_run_traceback_remaps_to_lpp_line -v
pytest -q
```

Expected: new test PASSES; full suite still passes (298 tests).

- [ ] **Step 6: Commit**

```bash
git add src/lpp/cli.py tests/test_cli.py
git commit -m "feat(cli): remap --run tracebacks to .lpp source lines"
```

---

## Self-Review

**Spec coverage:**
- ✅ `line` field on all Statement nodes → Task 1
- ✅ Parser captures and stores line numbers → Task 1
- ✅ Transpiler emits `# lpp:N` markers → Task 2
- ✅ `--run` traceback rewriting → Task 3
- ✅ `--run` shows L++ source line in traceback → Task 3 (`_install_run_hook` reads `lpp_src`)

**Placeholder scan:** None found.

**Type consistency:**
- `node.line: int | None = None` — consistent across all 24 nodes
- `_build_line_map(python_src: str) -> dict[int, int]` — used in Task 3 Step 4
- `_install_run_hook(lpp_path: str, lpp_src: str, line_map: dict[int, int]) -> None` — used in Task 3 Step 4
- `source` variable in `main()` already exists at the point where `_install_run_hook` is called (read at line ~161 of current `cli.py`)
