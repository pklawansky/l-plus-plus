# Decorator Support Design

**Date:** 2026-04-17
**Status:** Approved

---

## Goal

Add Python decorator support to L++ so that `@staticmethod`, `@property`, `@dataclass`, `@app.route("/")`, and similar patterns can be expressed without leaving the language.

---

## Disambiguation Rule

`@` already means "self/current instance context" in L++ (`@name` → `self.name`). Decorators also use `@` in Python. The conflict is resolved by position:

- `@expr` on its own line immediately before `fn` or `cls` = **decorator**
- `@expr` anywhere else = **self-attribute reference** (existing behaviour, unchanged)

Decorators stack: multiple consecutive `@expr` lines before `fn`/`cls` all apply, in order (outermost first, matching Python semantics).

The check is performed with a paren-depth-aware forward scan so complex expressions like `@app.route("/")` and `@lru_cache(maxsize=128)` are handled correctly — open parens prevent the newline from terminating the lookahead scan prematurely.

### Examples

```
@staticmethod
fn foo x
  x*2
# → @staticmethod
#   def foo(x):
#       return x * 2

@classmethod
@cache
fn bar cls n
  n

@lru_cache(maxsize=128)
fn fib n
  n

@dataclass
cls Point
  fn @init x y
    @x=x
    @y=y
```

---

## Changes

### `src/lpp/ast_nodes.py`

`FunctionDef` and `ClassDef` each gain:

```python
decorators: list[Expression] = field(default_factory=list)
```

Backwards-compatible — existing code constructing these nodes without the field gets an empty list.

### `src/lpp/parser.py`

**New method: `_is_decorator_context() -> bool`**

Saves position, scans forward skipping `@expr NEWLINE` lines (paren-depth-aware to handle call expressions), checks whether `fn` or `cls` follows. Restores position unconditionally. Returns `True` if a decorator pattern is detected.

```
_is_decorator_context:
  save pos
  while peek == AT:
    advance past @
    scan tokens until NEWLINE at depth 0 (track LPAREN/RPAREN/LBRACKET/RBRACKET depth)
    advance past NEWLINE
    skip_newlines
  return peek in (DEF, CLASS)   # DEF is the TokenType for the `fn` keyword
  restore pos
```

**New method: `_collect_decorators() -> list[Expression]`**

Consumes `@expr NEWLINE` sequences. The expression after `@` is parsed as a plain expression via `parse_expression()` — not through `_try_parse_self_attr_assign`. Returns the list of decorator expressions.

**`_parse_statement` guard (one new block at top):**

```python
if self.peek_type() == TokenType.AT and self._is_decorator_context():
    decorators = self._collect_decorators()
    if self.peek_type() == TokenType.DEF:
        return self._parse_function(decorators)
    else:
        return self._parse_class(decorators)
```

**`_parse_function(decorators=[])` and `_parse_class(decorators=[])`**

Both accept an optional `decorators` parameter (default empty list) and pass it through to the AST node. No other change to these methods.

**`_parse_class` inner loop**

`_parse_class` calls `_parse_function` directly (not via `_parse_statement`), so the `_parse_statement` guard never fires for methods. The inner loop must also check for decorators:

```python
while not self.match(TokenType.DEDENT, TokenType.EOF):
    method_decorators = []
    if self.peek_type() == TokenType.AT and self._is_decorator_context():
        method_decorators = self._collect_decorators()
    methods.append(self._parse_function(method_decorators))
    self.skip_newlines()
```

This covers `@property`, `@classmethod`, `@staticmethod`, and arbitrary decorators on methods.

### `src/lpp/transpiler.py`

**`_fn()`:** Before emitting `def name(...):`, emit each decorator at the same indentation depth:

```python
for dec in node.decorators:
    lines.append(f"{pad}@{self._expr(dec)}")
```

**`_cls()`:** Same pattern before `class Name(Base):`.

No new transpiler methods needed — `_expr()` already handles names, attribute access, and calls.

---

## Test Plan

### New tests (`tests/test_transpiler.py`)

| Scenario | L++ | Expected Python output |
|----------|-----|----------------------|
| Simple decorator on fn | `@staticmethod\nfn foo x\n  x*2\n` | `@staticmethod\ndef foo(x):\n    return x * 2` |
| Stacked decorators | `@classmethod\n@cache\nfn bar cls n\n  n\n` | `@classmethod\n@cache\ndef bar(cls, n):\n    return n` |
| Call decorator | `@lru_cache(maxsize=128)\nfn fib n\n  n\n` | `@lru_cache(maxsize=128)\ndef fib(n):\n    return n` |
| Attribute decorator | `@app.route("/")\nfn index\n  "hi"\n` | `@app.route("/")\ndef index():\n    return "hi"` |
| Decorator on class | `@dataclass\ncls Point\n  fn @init x\n    @x=x\n` | `@dataclass\nclass Point:\n    def __init__(self, x):\n        self.x = x` |
| Decorator on method | `cls Foo\n  @property\n  fn @bar\n    @_bar\n` | `class Foo:\n    @property\n    def bar(self):\n        return self._bar` |

### Regression: `@attr` unchanged

Existing self-attribute tests must all pass. Specifically:
- `@x` not before `fn`/`cls` → `self.x`
- `@x=1` → `self.x = 1`
- `@x+=1` → `self.x += 1`

### New parser tests (`tests/test_parser.py`)

- `@staticmethod\nfn foo x\n  x\n` → `FunctionDef` with `decorators=[Name("staticmethod")]`
- Stacked decorators → `decorators` list in correct order
- `@x\np(@x)\n` (no fn/cls after) → not treated as decorator; ExprStatement + Call

---

## Out of Scope

- Decorator expressions spanning multiple lines
- Interaction with `alias` / `use` for decorator names (decorators use names already in scope, same as Python)
