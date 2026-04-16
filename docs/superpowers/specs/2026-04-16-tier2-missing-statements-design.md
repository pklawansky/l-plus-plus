# Tier 2: Missing Core Statements Design

**Date:** 2026-04-16
**Status:** Approved

---

## Goal

Add the Python statements that L++ cannot currently express: `break`, `continue`, `raise`, `with`/`as`, `global`, `nonlocal`, `try/finally`, and full assignment target support (subscript, attribute, unpacking).

---

## Master Principle

1:1 parity with Python. Every Python statement that an LLM would need to write quality code must be expressible in L++.

---

## Section 1: New Keywords

Eight new keywords added to `src/lpp/tokens.py` (`TokenType` enum + `KEYWORDS` dict):

| Keyword | Purpose | Notes |
|---------|---------|-------|
| `break` | Exit loop | |
| `continue` | Skip to next iteration | |
| `raise` | Throw exception | |
| `with` | Context manager block | |
| `as` | Bind context manager / exception result | Was removed (dead); now has real use |
| `fin` | `finally` clause | Short form — `finally` is long |
| `global` | Declare global scope variable | |
| `nl` | Declare enclosing scope variable | `nonlocal` is multi-token (ids=[6414,2497]); shortened to `nl` (validated 2026-04-16) |

`nl` is the L++ keyword; the transpiler emits Python's `nonlocal`. Run `tools/validate_tokens.py` after adding new keywords to check all 9.

---

## Section 2: AST Changes

File: `src/lpp/ast_nodes.py`

### New statement nodes

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
    names: list[str]   # L++ keyword: nl; Python output: nonlocal

@dataclass
class UnpackAssignment:
    targets: list[Expression]   # Name("a") for plain, Spread(Name("b")) for *b
    value: Expression
```

### Modified existing nodes

**`TryStatement`** — add one optional field:
```python
@dataclass
class TryStatement:
    body: list[Statement]
    handlers: list[ErrHandler]
    finally_body: list[Statement] | None = None  # NEW
```

**`Assignment`** — widen `target` type:
```python
@dataclass
class Assignment:
    target: str | Expression    # str for simple names; Expression for subscript/attribute
    value: Expression
```

**`AugAssignment`** — same widening:
```python
@dataclass
class AugAssignment:
    target: str | Expression
    op: str
    value: Expression
```

The `str` case is backward-compatible — all existing uses continue to work.

### `Statement` union

Add all new nodes to the `Statement` union at the top of `ast_nodes.py`:
```python
Statement = Union[
    "FunctionDef", "ClassDef", "Assignment", "AugAssignment",
    "IfStatement", "ForStatement", "DoStatement", "TryStatement",
    "RetStatement", "UseStatement", "AliasStatement",
    "AppendStatement", "ExprStatement",
    "BreakStatement", "ContinueStatement", "RaiseStatement",    # NEW
    "WithStatement", "GlobalStatement", "NonlocalStatement",    # NEW
    "UnpackAssignment",                                         # NEW
]
```

---

## Section 3: Parser Changes

File: `src/lpp/parser.py`

### New dispatch in `_parse_statement`

```python
if tt == TokenType.BREAK:    return self._parse_break()
if tt == TokenType.CONTINUE: return self._parse_continue()
if tt == TokenType.RAISE:    return self._parse_raise()
if tt == TokenType.WITH:     return self._parse_with()
if tt == TokenType.GLOBAL:   return self._parse_global()
if tt == TokenType.NL: return self._parse_nonlocal()
```

### Simple statement parsers

```python
def _parse_break(self) -> BreakStatement:
    self.expect(TokenType.BREAK)
    if self.match(TokenType.NEWLINE): self.advance()
    return BreakStatement()

def _parse_continue(self) -> ContinueStatement:
    self.expect(TokenType.CONTINUE)
    if self.match(TokenType.NEWLINE): self.advance()
    return ContinueStatement()

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

### `_parse_raise`

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

Note: `FROM` needs to be a token type. Add `FROM = auto()` to `TokenType` and `"from": TokenType.FROM` to `KEYWORDS`.

Wait — `from` is a 9th new keyword. Add it to Section 1.

### `_parse_with`

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

### Extended `_parse_try`

After collecting `err` handlers, check for `fin`:

```python
finally_body = None
if self.match(TokenType.FIN):
    self.advance()
    self.skip_newlines()
    finally_body = self._parse_block()

# Relax the "requires err handler" check:
if not handlers and finally_body is None:
    tok = self.peek()
    raise ParseError(
        "try block requires at least one err handler or fin clause",
        line=tok.line, col=tok.col
    )
return TryStatement(body, handlers, finally_body)
```

### Rewritten `_parse_expr_or_assign`

Approach A: parse expression first, then check what follows.

```python
def _parse_expr_or_assign(self) -> Statement:
    save = self.pos

    # Path 1: @attr assignment / aug-assignment (unchanged)
    if self.peek_type() == TokenType.AT:
        self.advance()
        attr = self.expect(TokenType.IDENT).value
        AUG = {TokenType.PLUSEQ: "+=", TokenType.MINUSEQ: "-=",
               TokenType.STAREQ: "*=", TokenType.SLASHEQ: "/="}
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
        if len(targets) == 1 and isinstance(targets[0], Name):
            return Assignment(targets[0].id, value)
        return UnpackAssignment(targets, value)

    # Path 3: Full expression, then check operator
    self.pos = save
    expr = self.parse_expression()
    AUG = {TokenType.PLUSEQ: "+=", TokenType.MINUSEQ: "-=",
           TokenType.STAREQ: "*=", TokenType.SLASHEQ: "/="}
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
    Returns list of Name/Spread(Name) nodes if successful, None otherwise.
    Resets position on failure."""
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
            # Single target without comma — not unpacking, fall through to Path 3
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

Note: `_try_parse_unpack_targets` requires at least 2 targets (a comma was seen) before committing. A single `ident =` is handled by Path 3.

---

## Section 4: Transpiler Changes

File: `src/lpp/transpiler.py`

Add to `_stmt` match:

```python
case BreakStatement():
    return f"{pad}break"

case ContinueStatement():
    return f"{pad}continue"

case RaiseStatement(exc, cause):
    if exc is None:
        return f"{pad}raise"
    elif cause is None:
        return f"{pad}raise {self._expr(exc)}"
    else:
        return f"{pad}raise {self._expr(exc)} from {self._expr(cause)}"

case GlobalStatement(names):
    return f"{pad}global {', '.join(names)}"

case NonlocalStatement(names):
    return f"{pad}nonlocal {', '.join(names)}"

case WithStatement(items, body):
    parts = []
    for expr, name in items:
        parts.append(f"{self._expr(expr)} as {name}" if name else self._expr(expr))
    header = f"{pad}with {', '.join(parts)}:"
    lines = [header] + [self._stmt(s, depth + 1) for s in body]
    return "\n".join(lines)

case UnpackAssignment(targets, value):
    tgt = ", ".join(
        f"*{self._expr(t.value)}" if isinstance(t, Spread) else self._expr(t)
        for t in targets
    )
    return f"{pad}{tgt} = {self._expr(value)}"
```

Update existing cases:

```python
case Assignment(target, value):
    tgt = target if isinstance(target, str) else self._expr(target)
    return f"{pad}{tgt} = {self._expr(value)}"

case AugAssignment(target, op, value):
    tgt = target if isinstance(target, str) else self._expr(target)
    return f"{pad}{tgt} {op} {self._expr(value)}"
```

Update `_try` to emit `finally`:

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

---

## Section 5: Testing

### Parser tests (`tests/test_parser.py`)

```python
# break / continue
test_parse_break         — ForStatement body contains BreakStatement()
test_parse_continue      — ForStatement body contains ContinueStatement()

# raise
test_parse_raise_bare    — RaiseStatement(None, None)
test_parse_raise_expr    — RaiseStatement(Call(Name("ValueError"), [StringLiteral(...)]), None)
test_parse_raise_from    — RaiseStatement(exc=..., cause=Name("orig"))

# with
test_parse_with_as       — WithStatement([(Call(...), "fh")], body)
test_parse_with_no_as    — WithStatement([(Call(...), None)], body)
test_parse_with_multi    — WithStatement with 2 items

# global / nonlocal
test_parse_global        — GlobalStatement(["x", "y"])
test_parse_nonlocal      — NonlocalStatement(["x"])  # L++ source: "nl x\n"

# try/finally
test_parse_try_finally          — TryStatement.finally_body is not None
test_parse_try_only_fin         — no err handlers, only fin clause, valid
test_parse_try_err_and_fin      — both err handlers and fin clause

# assignment targets
test_parse_subscript_assign     — Assignment(Subscript(Name("d"), Name("k")), Name("v"))
test_parse_attr_assign          — Assignment(Attribute(Name("obj"), "attr"), Name("v"))
test_parse_unpack_assign        — UnpackAssignment([Name("a"), Name("b")], ...)
test_parse_star_unpack          — UnpackAssignment([Name("a"), Spread(Name("b"))], ...)
test_parse_subscript_aug        — AugAssignment(Subscript(...), "+=", ...)
test_parse_attr_aug             — AugAssignment(Attribute(...), "+=", ...)
```

### Transpiler tests (`tests/test_transpiler.py`)

```python
test_break                — py("for i in r(1)\n  break\n") contains "break"
test_continue             — contains "continue"
test_raise_bare           — py("raise\n") == "raise"
test_raise_expr           — contains "raise ValueError"
test_raise_from           — contains "raise ValueError() from orig"
test_with                 — contains "with open(\"f\") as fh:"
test_with_no_as           — contains "with lock():"
test_global               — py("global x,y\n") == "global x, y"
test_nonlocal             — py("nl x\n") == "nonlocal x"
test_try_finally          — contains "finally:"
test_try_only_fin         — valid try/finally with no except
test_subscript_assign     — py("d[k]=v\n") == "d[k] = v"
test_attr_assign          — py("obj.attr=v\n") == "obj.attr = v"
test_unpack_assign        — py("a,b=fn!\n") == "a, b = fn()"
test_star_unpack          — py("a,*b=lst\n") == "a, *b = lst"
test_subscript_aug        — py("d[k]+=1\n") == "d[k] += 1"
test_attr_aug             — py("obj.attr+=1\n") == "obj.attr += 1"
```

### Integration tests (`tests/test_integration.py`)

```python
test_break_exits_loop     — loop with break exits after first iteration
test_raise_caught         — raise inside try/err fires handler
test_with_file            — write+read file via context manager
test_global_mutation      — fn mutates global var declared with `global`
test_finally_runs         — finally block runs even when exception raised
test_unpack_roundtrip     — a,b=1,2 then print both
```

### cl100k validation

Run `tools/validate_tokens.py` after adding all 9 new keywords (`from` included). If `nonlocal` is multi-token, rename to `nl` in `TokenType`, `KEYWORDS`, and this spec before proceeding.

---

## New Keywords Summary (corrected — 9 total)

`break`, `continue`, `raise`, `with`, `as`, `fin`, `global`, `nl`, `from`

`nl` is the L++ keyword for Python's `nonlocal` (`nonlocal` itself is 2 cl100k tokens). The transpiler emits `nonlocal` in Python output.
`from` is needed for `raise X from Y`. It has no conflict with L++ import syntax (which uses `use`, not `from`).

---

## Out of Scope

- Decorator syntax — deferred (requires design; `@` is taken)
- `yield` / generator functions — Tier 6
- `async`/`await` — Tier 6
- Type annotations — Tier 4
- `del` statement — low priority, can be added later
- `pass` statement — already emitted for empty function bodies; not needed as standalone (use empty block)
