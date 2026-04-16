# Tier 2: Missing Core Statements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `break`, `continue`, `raise`/`from`, `with`/`as`, `global`, `nl` (nonlocal), `try/finally` (`fin`), and full assignment-target support (subscript, attribute, unpacking) to L++.

**Architecture:** Foundation-first — add tokens and AST nodes in isolated tasks (Tasks 1–3), then implement each statement feature TDD-style (Tasks 4–9), finishing with integration tests (Task 10). The big `_parse_expr_or_assign` rewrite (Task 9) uses Approach A: parse full expression then check operator, enabling subscript/attribute/unpack targets without fragile lookahead.

**Tech Stack:** Python 3.11+, pytest, tiktoken (for cl100k validation)

---

## File Structure

```
src/lpp/tokens.py        Add 9 new TokenType values + KEYWORDS entries
src/lpp/ast_nodes.py     Add 7 new dataclasses; widen Assignment/AugAssignment.target; extend TryStatement
src/lpp/parser.py        Add 8 new parse methods; extend _parse_try; rewrite _parse_expr_or_assign + add _try_parse_unpack_targets
src/lpp/transpiler.py    Add 7 new _stmt cases; update Assignment/AugAssignment cases; extend _try
tests/test_parser.py     ~18 new parser tests
tests/test_transpiler.py ~17 new transpiler tests
tests/test_integration.py 6 new integration tests
```

---

## Task 1: Validate `nonlocal` keyword with cl100k

**Files:**
- Read: `tools/validate_tokens.py` (reference for how to invoke tiktoken)

The spec requires confirming `nonlocal` is a single cl100k token before committing to that keyword name. If it's multi-token, every occurrence of `NONLOCAL`/`"nonlocal"` in Tasks 2–10 must be replaced with `NL`/`"nl"`.

- [ ] **Step 1: Run the cl100k check for `nonlocal`**

```bash
python -c "
import tiktoken
enc = tiktoken.get_encoding('cl100k_base')
word = 'nonlocal'
ids = enc.encode(word)
print(f'{word!r}: {len(ids)} token(s) — ids={ids}')
print('PASS: single token' if len(ids) == 1 else 'FAIL: multi-token — rename to nl')
"
```

Expected: `'nonlocal': 1 token(s)` → PASS. If FAIL, all Task 2–10 steps that say `NONLOCAL` / `"nonlocal"` must use `NL` / `"nl"` instead (a simple search-replace in those steps before running them).

---

## Task 2: Add 9 new token types + keywords to `tokens.py`

**Files:**
- Modify: `src/lpp/tokens.py:4-76`

- [ ] **Step 1: Add 9 new `TokenType` enum values**

In `src/lpp/tokens.py`, replace:
```python
    USE = auto()
    ALIAS = auto()
```
with:
```python
    USE = auto()
    ALIAS = auto()
    BREAK = auto()
    CONTINUE = auto()
    RAISE = auto()
    WITH = auto()
    AS = auto()
    FIN = auto()
    GLOBAL = auto()
    NL = auto()
    FROM = auto()
```

- [ ] **Step 2: Add 9 new entries to the `KEYWORDS` dict**

In `src/lpp/tokens.py`, replace:
```python
    "use": TokenType.USE,
    "alias": TokenType.ALIAS,
}
```
with:
```python
    "use": TokenType.USE,
    "alias": TokenType.ALIAS,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "raise": TokenType.RAISE,
    "with": TokenType.WITH,
    "as": TokenType.AS,
    "fin": TokenType.FIN,
    "global": TokenType.GLOBAL,
    "nl": TokenType.NL,
    "from": TokenType.FROM,
}
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

```bash
pytest -q
```

Expected: all 118 tests pass (no behavior changed, only new enum values added).

- [ ] **Step 4: Run cl100k validation for all keywords**

```bash
python tools/validate_tokens.py
```

Expected: all keywords single-token.

- [ ] **Step 5: Commit**

```bash
git add src/lpp/tokens.py
git commit -m "feat: add 9 new keyword token types (Tier 2)"
```

---

## Task 3: Add new AST nodes + extend existing nodes in `ast_nodes.py`

**Files:**
- Modify: `src/lpp/ast_nodes.py`

- [ ] **Step 1: Update the `Statement` union**

In `src/lpp/ast_nodes.py`, replace:
```python
Statement = Union[
    "FunctionDef", "ClassDef", "Assignment", "AugAssignment",
    "IfStatement", "ForStatement", "DoStatement", "TryStatement",
    "RetStatement", "UseStatement", "AliasStatement",
    "AppendStatement", "ExprStatement",
]
```
with:
```python
Statement = Union[
    "FunctionDef", "ClassDef", "Assignment", "AugAssignment",
    "IfStatement", "ForStatement", "DoStatement", "TryStatement",
    "RetStatement", "UseStatement", "AliasStatement",
    "AppendStatement", "ExprStatement",
    "BreakStatement", "ContinueStatement", "RaiseStatement",
    "WithStatement", "GlobalStatement", "NonlocalStatement",
    "UnpackAssignment",
]
```

- [ ] **Step 2: Widen `Assignment.target` and `AugAssignment.target`**

In `src/lpp/ast_nodes.py`, replace:
```python
@dataclass
class Assignment:
    target: str
    value: Expression
```
with:
```python
@dataclass
class Assignment:
    target: str | Expression    # str for simple names; Expression for subscript/attribute
    value: Expression
```

Replace:
```python
@dataclass
class AugAssignment:
    target: str
    op: str            # +=, -=, *=, /=
    value: Expression
```
with:
```python
@dataclass
class AugAssignment:
    target: str | Expression
    op: str            # +=, -=, *=, /=
    value: Expression
```

- [ ] **Step 3: Add `finally_body` field to `TryStatement`**

In `src/lpp/ast_nodes.py`, replace:
```python
@dataclass
class TryStatement:
    body: list[Statement]
    handlers: list["ErrHandler"]
```
with:
```python
@dataclass
class TryStatement:
    body: list[Statement]
    handlers: list["ErrHandler"]
    finally_body: list[Statement] | None = None
```

- [ ] **Step 4: Add 7 new statement dataclasses**

After the `ExprStatement` class (line ~108), add:

```python
@dataclass
class BreakStatement:
    pass

@dataclass
class ContinueStatement:
    pass

@dataclass
class RaiseStatement:
    exc: Expression | None      # None = bare `raise` (re-raise current exception)
    cause: Expression | None    # None = no `from` clause

@dataclass
class WithStatement:
    items: list[tuple[Expression, str | None]]  # (expr, binding_name); name=None if no `as`
    body: list[Statement]

@dataclass
class GlobalStatement:
    names: list[str]

@dataclass
class NonlocalStatement:
    names: list[str]

@dataclass
class UnpackAssignment:
    targets: list[Expression]   # Name("a") for plain names, Spread(Name("b")) for *b
    value: Expression
```

- [ ] **Step 5: Run existing tests to verify nothing broke**

```bash
pytest -q
```

Expected: all 118 tests pass (field widening is backward-compatible; `finally_body=None` default preserves existing behavior).

- [ ] **Step 6: Commit**

```bash
git add src/lpp/ast_nodes.py
git commit -m "feat: add 7 new AST nodes and extend TryStatement/Assignment for Tier 2"
```

---

## Task 4: `break` and `continue`

**Files:**
- Modify: `src/lpp/parser.py`
- Modify: `src/lpp/transpiler.py`
- Test: `tests/test_parser.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_parser.py`:

```python
def test_parse_break():
    src = "for i in r(1)\n  break\n"
    node = first(src)
    assert isinstance(node, ForStatement)
    assert isinstance(node.body[0], BreakStatement)

def test_parse_continue():
    src = "for i in r(1)\n  continue\n"
    node = first(src)
    assert isinstance(node, ForStatement)
    assert isinstance(node.body[0], ContinueStatement)
```

Append to `tests/test_transpiler.py`:

```python
def test_break():
    result = py("for i in r(1)\n  break\n")
    assert "break" in result

def test_continue():
    result = py("for i in r(1)\n  continue\n")
    assert "continue" in result
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_parser.py::test_parse_break tests/test_parser.py::test_parse_continue tests/test_transpiler.py::test_break tests/test_transpiler.py::test_continue -v
```

Expected: all 4 FAIL (BREAK/CONTINUE not dispatched in `_parse_statement`).

- [ ] **Step 3: Add dispatch + parsers in `parser.py`**

In `src/lpp/parser.py`, in `_parse_statement`, after `if tt == TokenType.ALIAS: return self._parse_alias()` (the last existing dispatch, around line 330), add:

```python
        if tt == TokenType.BREAK:    return self._parse_break()
        if tt == TokenType.CONTINUE: return self._parse_continue()
```

Then add two new methods immediately after `_parse_alias` (before `_parse_expr_or_assign`):

```python
    def _parse_break(self) -> BreakStatement:
        self.expect(TokenType.BREAK)
        if self.match(TokenType.NEWLINE): self.advance()
        return BreakStatement()

    def _parse_continue(self) -> ContinueStatement:
        self.expect(TokenType.CONTINUE)
        if self.match(TokenType.NEWLINE): self.advance()
        return ContinueStatement()
```

- [ ] **Step 4: Add transpiler cases in `transpiler.py`**

In `src/lpp/transpiler.py`, in the `_stmt` match block, after `case ExprStatement(expr):` add:

```python
            case BreakStatement():
                return f"{pad}break"
            case ContinueStatement():
                return f"{pad}continue"
```

- [ ] **Step 5: Run new tests to verify they pass**

```bash
pytest tests/test_parser.py::test_parse_break tests/test_parser.py::test_parse_continue tests/test_transpiler.py::test_break tests/test_transpiler.py::test_continue -v
```

Expected: all 4 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/lpp/parser.py src/lpp/transpiler.py tests/test_parser.py tests/test_transpiler.py
git commit -m "feat: add break and continue statements (Tier 2)"
```

---

## Task 5: `global` and `nonlocal`

**Files:**
- Modify: `src/lpp/parser.py`
- Modify: `src/lpp/transpiler.py`
- Test: `tests/test_parser.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_parser.py`:

```python
def test_parse_global():
    node = first("global x,y\n")
    assert isinstance(node, GlobalStatement)
    assert node.names == ["x", "y"]

def test_parse_nonlocal():
    node = first("nl x\n")
    assert isinstance(node, NonlocalStatement)
    assert node.names == ["x"]
```

Append to `tests/test_transpiler.py`:

```python
def test_global():
    assert py("global x,y\n") == "global x, y"

def test_nonlocal():
    assert py("nl x\n") == "nonlocal x"
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_parser.py::test_parse_global tests/test_parser.py::test_parse_nonlocal tests/test_transpiler.py::test_global tests/test_transpiler.py::test_nonlocal -v
```

Expected: all 4 FAIL.

- [ ] **Step 3: Add dispatch + parsers in `parser.py`**

In `_parse_statement`, add after the CONTINUE dispatch added in Task 4:

```python
        if tt == TokenType.GLOBAL:   return self._parse_global()
        if tt == TokenType.NL: return self._parse_nonlocal()
```

Add new methods after `_parse_continue`:

```python
    def _parse_global(self) -> GlobalStatement:
        self.expect(TokenType.GLOBAL)
        names = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.COMMA):
            self.advance()
            names.append(self.expect(TokenType.IDENT).value)
        if self.match(TokenType.NEWLINE): self.advance()
        return GlobalStatement(names)

    def _parse_nonlocal(self) -> NonlocalStatement:
        self.expect(TokenType.NL)
        names = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.COMMA):
            self.advance()
            names.append(self.expect(TokenType.IDENT).value)
        if self.match(TokenType.NEWLINE): self.advance()
        return NonlocalStatement(names)
```

- [ ] **Step 4: Add transpiler cases in `transpiler.py`**

After the `ContinueStatement()` case added in Task 4, add:

```python
            case GlobalStatement(names):
                return f"{pad}global {', '.join(names)}"
            case NonlocalStatement(names):
                return f"{pad}nonlocal {', '.join(names)}"
```

- [ ] **Step 5: Run new tests to verify they pass**

```bash
pytest tests/test_parser.py::test_parse_global tests/test_parser.py::test_parse_nonlocal tests/test_transpiler.py::test_global tests/test_transpiler.py::test_nonlocal -v
```

Expected: all 4 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/lpp/parser.py src/lpp/transpiler.py tests/test_parser.py tests/test_transpiler.py
git commit -m "feat: add global and nonlocal statements (Tier 2)"
```

---

## Task 6: `raise` with `from`

**Files:**
- Modify: `src/lpp/parser.py`
- Modify: `src/lpp/transpiler.py`
- Test: `tests/test_parser.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_parser.py`:

```python
def test_parse_raise_bare():
    node = first("raise\n")
    assert isinstance(node, RaiseStatement)
    assert node.exc is None
    assert node.cause is None

def test_parse_raise_expr():
    node = first("raise ValueError(\"oops\")\n")
    assert isinstance(node, RaiseStatement)
    assert isinstance(node.exc, Call)
    assert node.cause is None

def test_parse_raise_from():
    node = first("raise ValueError(\"oops\") from orig\n")
    assert isinstance(node, RaiseStatement)
    assert isinstance(node.exc, Call)
    assert node.cause == Name("orig")
```

Append to `tests/test_transpiler.py`:

```python
def test_raise_bare():
    assert py("raise\n") == "raise"

def test_raise_expr():
    assert "raise ValueError" in py("raise ValueError(\"oops\")\n")

def test_raise_from():
    result = py("raise ValueError(\"oops\") from orig\n")
    assert "raise ValueError" in result
    assert "from orig" in result
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_parser.py::test_parse_raise_bare tests/test_parser.py::test_parse_raise_expr tests/test_parser.py::test_parse_raise_from tests/test_transpiler.py::test_raise_bare tests/test_transpiler.py::test_raise_expr tests/test_transpiler.py::test_raise_from -v
```

Expected: all 6 FAIL.

- [ ] **Step 3: Add dispatch + parser in `parser.py`**

In `_parse_statement`, add after the NL dispatch added in Task 5:

```python
        if tt == TokenType.RAISE:    return self._parse_raise()
```

Add new method after `_parse_nonlocal`:

```python
    def _parse_raise(self) -> RaiseStatement:
        self.expect(TokenType.RAISE)
        exc = None
        cause = None
        if not self.match(TokenType.NEWLINE, TokenType.EOF):
            exc = self.parse_expression()
            if self.match(TokenType.FROM):
                self.advance()
                cause = self.parse_expression()
        if self.match(TokenType.NEWLINE): self.advance()
        return RaiseStatement(exc, cause)
```

- [ ] **Step 4: Add transpiler case in `transpiler.py`**

After the `NonlocalStatement` case added in Task 5, add:

```python
            case RaiseStatement(exc, cause):
                if exc is None:
                    return f"{pad}raise"
                elif cause is None:
                    return f"{pad}raise {self._expr(exc)}"
                else:
                    return f"{pad}raise {self._expr(exc)} from {self._expr(cause)}"
```

- [ ] **Step 5: Run new tests to verify they pass**

```bash
pytest tests/test_parser.py::test_parse_raise_bare tests/test_parser.py::test_parse_raise_expr tests/test_parser.py::test_parse_raise_from tests/test_transpiler.py::test_raise_bare tests/test_transpiler.py::test_raise_expr tests/test_transpiler.py::test_raise_from -v
```

Expected: all 6 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/lpp/parser.py src/lpp/transpiler.py tests/test_parser.py tests/test_transpiler.py
git commit -m "feat: add raise/from statement (Tier 2)"
```

---

## Task 7: `with` / `as`

**Files:**
- Modify: `src/lpp/parser.py`
- Modify: `src/lpp/transpiler.py`
- Test: `tests/test_parser.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_parser.py`:

```python
def test_parse_with_as():
    src = "with open(\"f\") as fh\n  p(fh)\n"
    node = first(src)
    assert isinstance(node, WithStatement)
    assert len(node.items) == 1
    expr, name = node.items[0]
    assert isinstance(expr, Call)
    assert name == "fh"

def test_parse_with_no_as():
    src = "with lock!\n  p(\"ok\")\n"
    node = first(src)
    assert isinstance(node, WithStatement)
    assert node.items[0][1] is None

def test_parse_with_multi():
    src = "with open(\"a\") as fa,open(\"b\") as fb\n  p(fa)\n"
    node = first(src)
    assert isinstance(node, WithStatement)
    assert len(node.items) == 2
    assert node.items[0][1] == "fa"
    assert node.items[1][1] == "fb"
```

Append to `tests/test_transpiler.py`:

```python
def test_with():
    result = py("with open(\"f\") as fh\n  p(fh)\n")
    assert 'with open("f") as fh:' in result

def test_with_no_as():
    result = py("with lock!\n  p(\"ok\")\n")
    assert "with lock():" in result

def test_with_multi():
    result = py("with open(\"a\") as fa,open(\"b\") as fb\n  p(fa)\n")
    assert "as fa" in result
    assert "as fb" in result
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_parser.py::test_parse_with_as tests/test_parser.py::test_parse_with_no_as tests/test_parser.py::test_parse_with_multi tests/test_transpiler.py::test_with tests/test_transpiler.py::test_with_no_as tests/test_transpiler.py::test_with_multi -v
```

Expected: all 6 FAIL.

- [ ] **Step 3: Add dispatch + parser in `parser.py`**

In `_parse_statement`, add after the RAISE dispatch added in Task 6:

```python
        if tt == TokenType.WITH:     return self._parse_with()
```

Add new method after `_parse_raise`:

```python
    def _parse_with(self) -> WithStatement:
        self.expect(TokenType.WITH)
        items = []
        while True:
            expr = self.parse_expression()
            name = None
            if self.match(TokenType.AS):
                self.advance()
                name = self.expect(TokenType.IDENT).value
            items.append((expr, name))
            if not self.match(TokenType.COMMA):
                break
            self.advance()
        self.skip_newlines()
        body = self._parse_block()
        return WithStatement(items, body)
```

- [ ] **Step 4: Add transpiler case in `transpiler.py`**

After the `RaiseStatement` case added in Task 6, add:

```python
            case WithStatement(items, body):
                parts = []
                for expr, name in items:
                    parts.append(f"{self._expr(expr)} as {name}" if name else self._expr(expr))
                header = f"{pad}with {', '.join(parts)}:"
                lines = [header] + [self._stmt(s, depth + 1) for s in body]
                return "\n".join(lines)
```

- [ ] **Step 5: Run new tests to verify they pass**

```bash
pytest tests/test_parser.py::test_parse_with_as tests/test_parser.py::test_parse_with_no_as tests/test_parser.py::test_parse_with_multi tests/test_transpiler.py::test_with tests/test_transpiler.py::test_with_no_as tests/test_transpiler.py::test_with_multi -v
```

Expected: all 6 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/lpp/parser.py src/lpp/transpiler.py tests/test_parser.py tests/test_transpiler.py
git commit -m "feat: add with/as statement (Tier 2)"
```

---

## Task 8: `try/finally` — `fin` clause

**Files:**
- Modify: `src/lpp/parser.py` (`_parse_try`)
- Modify: `src/lpp/transpiler.py` (`_try`)
- Test: `tests/test_parser.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_parser.py`:

```python
def test_parse_try_finally():
    src = "try\n  x=1\nerr\n  x=2\nfin\n  p(\"done\")\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert len(node.handlers) == 1
    assert node.finally_body is not None
    assert len(node.finally_body) == 1

def test_parse_try_only_fin():
    src = "try\n  x=1\nfin\n  p(\"done\")\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert node.handlers == []
    assert node.finally_body is not None

def test_parse_try_err_and_fin():
    src = "try\n  x=1\nerr ValueError e\n  p(e)\nfin\n  p(\"done\")\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert len(node.handlers) == 1
    assert node.finally_body is not None
```

Append to `tests/test_transpiler.py`:

```python
def test_try_finally():
    src = "try\n  x=1\nerr\n  x=2\nfin\n  p(\"done\")\n"
    result = py(src)
    assert "finally:" in result
    assert 'p("done")' in result

def test_try_only_fin():
    src = "try\n  x=1\nfin\n  p(\"done\")\n"
    result = py(src)
    assert "try:" in result
    assert "finally:" in result
    assert "except" not in result
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_parser.py::test_parse_try_finally tests/test_parser.py::test_parse_try_only_fin tests/test_parser.py::test_parse_try_err_and_fin tests/test_transpiler.py::test_try_finally tests/test_transpiler.py::test_try_only_fin -v
```

Expected: all 5 FAIL. `test_parse_try_only_fin` fails with `ParseError: try block requires at least one err handler`.

- [ ] **Step 3: Extend `_parse_try` in `parser.py`**

In `src/lpp/parser.py`, replace the entire `_parse_try` method (currently lines 414–436):

```python
    def _parse_try(self) -> TryStatement:
        self.expect(TokenType.TRY)
        self.skip_newlines()
        body = self._parse_block()
        handlers = []
        while self.match(TokenType.ERR):
            self.advance()
            exc_type = None
            name = None
            if self.match(TokenType.IDENT):
                exc_type = self.advance().value
            if self.match(TokenType.IDENT):
                name = self.advance().value
            self.skip_newlines()
            hbody = self._parse_block()
            handlers.append(ErrHandler(exc_type, name, hbody))
        finally_body = None
        if self.match(TokenType.FIN):
            self.advance()
            self.skip_newlines()
            finally_body = self._parse_block()
        if not handlers and finally_body is None:
            tok = self.peek()
            raise ParseError(
                "try block requires at least one err handler or fin clause",
                line=tok.line, col=tok.col
            )
        return TryStatement(body, handlers, finally_body)
```

- [ ] **Step 4: Extend `_try` in `transpiler.py`**

In `src/lpp/transpiler.py`, replace the entire `_try` method (currently lines 122–134):

```python
    def _try(self, node: TryStatement, depth: int) -> str:
        pad = INDENT * depth
        lines = [f"{pad}try:"]
        lines += [self._stmt(s, depth + 1) for s in node.body]
        for h in node.handlers:
            if h.exc_type and h.name:
                lines.append(f"{pad}except {h.exc_type} as {h.name}:")
            elif h.exc_type:
                lines.append(f"{pad}except {h.exc_type}:")
            else:
                lines.append(f"{pad}except:")
            lines += [self._stmt(s, depth + 1) for s in h.body]
        if node.finally_body:
            lines.append(f"{pad}finally:")
            lines += [self._stmt(s, depth + 1) for s in node.finally_body]
        return "\n".join(lines)
```

- [ ] **Step 5: Run new tests to verify they pass**

```bash
pytest tests/test_parser.py::test_parse_try_finally tests/test_parser.py::test_parse_try_only_fin tests/test_parser.py::test_parse_try_err_and_fin tests/test_transpiler.py::test_try_finally tests/test_transpiler.py::test_try_only_fin -v
```

Expected: all 5 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/lpp/parser.py src/lpp/transpiler.py tests/test_parser.py tests/test_transpiler.py
git commit -m "feat: add try/finally (fin) clause (Tier 2)"
```

---

## Task 9: Assignment target widening — subscript, attribute, unpack

**Files:**
- Modify: `src/lpp/parser.py` (`_parse_expr_or_assign`, new `_try_parse_unpack_targets`)
- Modify: `src/lpp/transpiler.py` (`Assignment`, `AugAssignment`, new `UnpackAssignment` cases)
- Test: `tests/test_parser.py`
- Test: `tests/test_transpiler.py`

This is the largest single change. `_parse_expr_or_assign` is completely replaced with Approach A: parse full expression first, then check what operator follows. This enables `d[k]=v`, `obj.attr=v`, and `a,b=lst` without fragile per-case lookahead.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_parser.py`:

```python
def test_parse_subscript_assign():
    node = first("d[k]=v\n")
    assert isinstance(node, Assignment)
    assert node.target == Subscript(Name("d"), Name("k"))
    assert node.value == Name("v")

def test_parse_attr_assign():
    node = first("obj.attr=v\n")
    assert isinstance(node, Assignment)
    assert node.target == Attribute(Name("obj"), "attr")
    assert node.value == Name("v")

def test_parse_unpack_assign():
    node = first("a,b=fn!\n")
    assert isinstance(node, UnpackAssignment)
    assert node.targets == [Name("a"), Name("b")]
    assert node.value == ZeroArgCall(Name("fn"))

def test_parse_star_unpack():
    node = first("a,*b=lst\n")
    assert isinstance(node, UnpackAssignment)
    assert node.targets[0] == Name("a")
    assert node.targets[1] == Spread(Name("b"))

def test_parse_subscript_aug():
    node = first("d[k]+=1\n")
    assert isinstance(node, AugAssignment)
    assert node.target == Subscript(Name("d"), Name("k"))
    assert node.op == "+="

def test_parse_attr_aug():
    node = first("obj.attr+=1\n")
    assert isinstance(node, AugAssignment)
    assert node.target == Attribute(Name("obj"), "attr")
    assert node.op == "+="
```

Append to `tests/test_transpiler.py`:

```python
def test_subscript_assign():
    assert py("d[k]=v\n") == "d[k] = v"

def test_attr_assign():
    assert py("obj.attr=v\n") == "obj.attr = v"

def test_unpack_assign():
    assert py("a,b=fn!\n") == "a, b = fn()"

def test_star_unpack():
    assert py("a,*b=lst\n") == "a, *b = lst"

def test_subscript_aug():
    assert py("d[k]+=1\n") == "d[k] += 1"

def test_attr_aug():
    assert py("obj.attr+=1\n") == "obj.attr += 1"
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_parser.py::test_parse_subscript_assign tests/test_parser.py::test_parse_attr_assign tests/test_parser.py::test_parse_unpack_assign tests/test_parser.py::test_parse_star_unpack tests/test_parser.py::test_parse_subscript_aug tests/test_parser.py::test_parse_attr_aug tests/test_transpiler.py::test_subscript_assign tests/test_transpiler.py::test_attr_assign tests/test_transpiler.py::test_unpack_assign tests/test_transpiler.py::test_star_unpack tests/test_transpiler.py::test_subscript_aug tests/test_transpiler.py::test_attr_aug -v
```

Expected: all 12 FAIL.

- [ ] **Step 3: Replace `_parse_expr_or_assign` and add `_try_parse_unpack_targets` in `parser.py`**

In `src/lpp/parser.py`, replace the entire `_parse_expr_or_assign` method (currently lines 507–565) with:

```python
    def _parse_expr_or_assign(self) -> Statement:
        save = self.pos

        # Path 1: @attr assignment / aug-assignment
        if self.peek_type() == TokenType.AT:
            self.advance()
            attr = self.expect(TokenType.IDENT).value
            AUG = {
                TokenType.PLUSEQ: "+=", TokenType.MINUSEQ: "-=",
                TokenType.STAREQ: "*=", TokenType.SLASHEQ: "/=",
            }
            if self.peek_type() in AUG:
                op = AUG[self.advance().type]
                value = self.parse_expression()
                if self.match(TokenType.NEWLINE): self.advance()
                return AugAssignment(f"self.{attr}", op, value)
            if self.peek_type() == TokenType.EQ:
                self.advance()
                value = self.parse_expression()
                if self.match(TokenType.NEWLINE): self.advance()
                return Assignment(f"self.{attr}", value)
            self.pos = save

        # Path 2: Unpacking — (ident | *ident) (, (ident | *ident))+ =
        targets = self._try_parse_unpack_targets()
        if targets is not None:
            self.advance()  # skip =
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE): self.advance()
            return UnpackAssignment(targets, value)

        # Path 3: Full expression, then check operator
        self.pos = save
        expr = self.parse_expression()
        AUG = {
            TokenType.PLUSEQ: "+=", TokenType.MINUSEQ: "-=",
            TokenType.STAREQ: "*=", TokenType.SLASHEQ: "/=",
        }
        if self.peek_type() in AUG:
            op = AUG[self.advance().type]
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE): self.advance()
            target = expr.id if isinstance(expr, Name) else expr
            return AugAssignment(target, op, value)
        if self.match(TokenType.EQ):
            self.advance()
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE): self.advance()
            target = expr.id if isinstance(expr, Name) else expr
            return Assignment(target, value)
        if self.match(TokenType.APPEND):
            self.advance()
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE): self.advance()
            return AppendStatement(expr, value)
        if self.match(TokenType.NEWLINE): self.advance()
        return ExprStatement(expr)

    def _try_parse_unpack_targets(self) -> list[Expression] | None:
        """Try to parse a comma-separated target list followed by =.
        Returns list of Name/Spread(Name) nodes if >=2 targets found and = follows.
        Resets position on failure; a single ident= falls through to Path 3."""
        save = self.pos
        targets = []
        try:
            while True:
                if self.match(TokenType.STAR):
                    self.advance()
                    name = self.expect(TokenType.IDENT).value
                    targets.append(Spread(Name(name)))
                elif self.match(TokenType.IDENT):
                    targets.append(Name(self.advance().value))
                else:
                    self.pos = save
                    return None
                if not self.match(TokenType.COMMA):
                    break
                self.advance()
            if len(targets) < 2:
                # Single target — not an unpack; let Path 3 handle ident=
                self.pos = save
                return None
            if not self.match(TokenType.EQ):
                self.pos = save
                return None
            return targets
        except ParseError:
            self.pos = save
            return None
```

- [ ] **Step 4: Update transpiler `Assignment`, `AugAssignment`, add `UnpackAssignment` in `transpiler.py`**

In `src/lpp/transpiler.py`, in the `_stmt` match block, replace:

```python
            case Assignment(target, value):
                return f"{pad}{target} = {self._expr(value)}"
            case AugAssignment(target, op, value):
                return f"{pad}{target} {op} {self._expr(value)}"
```

with:

```python
            case Assignment(target, value):
                tgt = target if isinstance(target, str) else self._expr(target)
                return f"{pad}{tgt} = {self._expr(value)}"
            case AugAssignment(target, op, value):
                tgt = target if isinstance(target, str) else self._expr(target)
                return f"{pad}{tgt} {op} {self._expr(value)}"
            case UnpackAssignment(targets, value):
                tgt = ", ".join(
                    f"*{self._expr(t.value)}" if isinstance(t, Spread) else self._expr(t)
                    for t in targets
                )
                return f"{pad}{tgt} = {self._expr(value)}"
```

- [ ] **Step 5: Run new tests to verify they pass**

```bash
pytest tests/test_parser.py::test_parse_subscript_assign tests/test_parser.py::test_parse_attr_assign tests/test_parser.py::test_parse_unpack_assign tests/test_parser.py::test_parse_star_unpack tests/test_parser.py::test_parse_subscript_aug tests/test_parser.py::test_parse_attr_aug tests/test_transpiler.py::test_subscript_assign tests/test_transpiler.py::test_attr_assign tests/test_transpiler.py::test_unpack_assign tests/test_transpiler.py::test_star_unpack tests/test_transpiler.py::test_subscript_aug tests/test_transpiler.py::test_attr_aug -v
```

Expected: all 12 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest -q
```

Expected: all tests pass. Pay particular attention to existing assignment and aug-assignment tests — the rewrite must stay backward-compatible.

- [ ] **Step 7: Commit**

```bash
git add src/lpp/parser.py src/lpp/transpiler.py tests/test_parser.py tests/test_transpiler.py
git commit -m "feat: widen assignment targets to subscript, attribute, and unpack (Tier 2)"
```

---

## Task 10: Integration tests

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Write the failing integration tests**

Append to `tests/test_integration.py`:

```python
def test_break_exits_loop():
    src = textwrap.dedent("""\
        acc=[]
        for i in r(10)
          if i==3
            break
          acc<<i
        p(acc)
    """)
    assert run_lpp(src) == "[0, 1, 2]"

def test_raise_caught():
    src = textwrap.dedent("""\
        try
          raise ValueError("oops")
        err ValueError e
          p("caught")
    """)
    assert run_lpp(src) == "caught"

def test_with_file():
    src = textwrap.dedent("""\
        use os
        path="test_with_tmp.txt"
        with open(path,"w") as fh
          fh.write("hello")
        with open(path) as r
          content=r.read!
        os.unlink(path)
        p(content)
    """)
    assert run_lpp(src) == "hello"

def test_global_mutation():
    src = textwrap.dedent("""\
        x=0
        fn bump
          global x
          x+=1
        bump!
        bump!
        p(x)
    """)
    assert run_lpp(src) == "2"

def test_finally_runs():
    src = textwrap.dedent("""\
        log=[]
        try
          log<<1
          raise RuntimeError("e")
        err
          log<<2
        fin
          log<<3
        p(log)
    """)
    assert run_lpp(src) == "[1, 2, 3]"

def test_unpack_roundtrip():
    src = textwrap.dedent("""\
        a,b=[1,2]
        p(a)
        p(b)
    """)
    assert run_lpp(src) == "1\n2"
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_integration.py::test_break_exits_loop tests/test_integration.py::test_raise_caught tests/test_integration.py::test_with_file tests/test_integration.py::test_global_mutation tests/test_integration.py::test_finally_runs tests/test_integration.py::test_unpack_roundtrip -v
```

Expected: all 6 FAIL (the features aren't wired up in the L++ pipeline yet — wait, they are after Tasks 4–9! These will pass once the pipeline is complete. If run after Tasks 4–9, they should pass. If they fail here, re-run after ensuring all previous tasks are committed.)

- [ ] **Step 3: Run full suite**

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for Tier 2 statements"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|-----------------|------|
| `break` keyword + parser + transpiler | Task 4 |
| `continue` keyword + parser + transpiler | Task 4 |
| `global name[,name]` | Task 5 |
| `nl name[,name]` (Python: `nonlocal`) | Task 5 |
| `raise` bare / expr / `from` | Task 6 |
| `with expr [as name][, ...]` | Task 7 |
| `fin` finally clause | Task 8 |
| `try` without `err` (fin-only) | Task 8 |
| `Assignment.target` widened to `str | Expression` | Tasks 3 + 9 |
| `AugAssignment.target` widened | Tasks 3 + 9 |
| `d[k]=v` subscript assign | Task 9 |
| `obj.attr=v` attribute assign | Task 9 |
| `a,b=lst` unpack | Task 9 |
| `a,*b=lst` starred unpack | Task 9 |
| `d[k]+=1` subscript aug-assign | Task 9 |
| `obj.attr+=1` attribute aug-assign | Task 9 |
| 9 new tokens in `tokens.py` | Task 2 |
| 7 new AST nodes | Task 3 |
| cl100k validation for all 9 new keywords | Task 1 + Task 2 Step 4 |
| Integration: break exits loop | Task 10 |
| Integration: raise/catch | Task 10 |
| Integration: with file I/O | Task 10 |
| Integration: global mutation | Task 10 |
| Integration: finally runs | Task 10 |
| Integration: unpack roundtrip | Task 10 |

**Placeholder scan:** No TBDs. All code steps contain complete implementations.

**Type consistency:**
- `BreakStatement()`, `ContinueStatement()` defined in Task 3, used in Tasks 4.
- `GlobalStatement(names)`, `NonlocalStatement(names)` defined Task 3, used Task 5.
- `RaiseStatement(exc, cause)` defined Task 3, used Task 6.
- `WithStatement(items, body)` defined Task 3, used Task 7.
- `TryStatement.finally_body` added Task 3, used Task 8.
- `UnpackAssignment(targets, value)` defined Task 3, used Task 9.
- `Spread(Name(name))` — `Spread` already exists in `ast_nodes.py`.
- All `TokenType.BREAK`, `CONTINUE`, etc. added Task 2, used in respective tasks.
