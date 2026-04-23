# Type Annotation Syntax — Design Spec

**Date:** 2026-04-22  
**Status:** Approved

---

## Overview

Add optional type annotation syntax to L++ using `::` as the annotation operator. Annotations are passed through verbatim to Python output — no L++-level type checking. The `::` operator avoids all existing `:` conflicts (class bases, dict literals, slices).

---

## Syntax

```
# Variable annotation with value
x::int = 5

# Bare annotation (declaration only)
x::int

# Self-attr annotation
@name::str = "hello"

# Function parameter annotations
def f(x::int, y::str = "default")
    ...

# Return type annotation
def f(x::int)::bool
    ...

# Combined
def f(x::int, items::list[str])::dict[str, int]
    ...
```

Type expressions are full L++ expressions — `int`, `str`, `list[int]`, `dict[str, Any]`, `Optional[str]` all valid.

---

## Lexer & Tokens (`tokens.py`, `lexer.py`)

- Add `COLONCOLON = auto()` to `TokenType`
- Add `"::": TokenType.COLONCOLON` to `MAP2` in the lexer

MAP2 is checked before MAP1, so `::` is always consumed as one token. Single `:` behaviour is unchanged.

---

## AST Nodes (`ast_nodes.py`)

Extend existing nodes with optional annotation fields (all default `None` — zero impact on existing code):

```python
@dataclass
class Param:
    name: str
    default: Expression | None = None
    kind: str = "pos"
    annotation: Expression | None = None   # NEW

@dataclass
class Assignment:
    target: str | Expression
    value: Expression
    annotation: Expression | None = None   # NEW
    line: int | None = None

@dataclass
class FunctionDef:
    name: str
    params: list[Param]
    body: list[Statement]
    is_method: bool
    decorators: list = field(default_factory=list)
    return_annotation: Expression | None = None   # NEW
    line: int | None = None
```

New node for bare declarations:

```python
@dataclass
class AnnotationStatement:
    target: str | Expression
    annotation: Expression
    line: int | None = None
```

`AnnotationStatement` added to the `Statement` union.

---

## Parser (`parser.py`)

Four sites gain `COLONCOLON` handling:

1. **`_parse_params`** — after consuming param name, peek for `COLONCOLON` → call `parse_expression()` → store on `Param.annotation`
2. **`_parse_function`** — after `_parse_params()` returns, peek for `COLONCOLON` → call `parse_expression()` → store on `FunctionDef.return_annotation`
3. **`_parse_expr_or_assign` (Path 3)** — after parsing LHS expression, peek for `COLONCOLON`:
   - Parse annotation via `parse_expression()`
   - If `EQ` follows: produce `Assignment(target, value, annotation=...)`
   - Otherwise: produce `AnnotationStatement(target, annotation)`
4. **`_try_parse_self_attr_assign`** — after `@name`, peek for `COLONCOLON` → parse annotation → require `EQ` → produce `Assignment("self.name", value, annotation=...)`

---

## Transpiler (`transpiler.py`)

| L++ | Python output |
|-----|--------------|
| `x::int = 5` | `x: int = 5` |
| `x::int` | `x: int` |
| `@x::str = "hi"` | `self.x: str = "hi"` |
| `def f(x::int)` | `def f(x: int):` |
| `def f()::bool` | `def f() -> bool:` |
| `def f(x::int)::bool` | `def f(x: int) -> bool:` |

Changes:
- `_fn`: annotated params emit `name: type`; `return_annotation` appends ` -> type` to the `def` line
- `Assignment` case: emit `target: type = value` when `annotation` is set
- New `AnnotationStatement` case: emit `target: type`

---

## LSP / Semantic (`semantic.py`, `server.py`)

- **`semantic.py`**: `AnnotationStatement` defines the target name in the current scope (prevents false "undeclared variable" diagnostics on subsequent uses); walk the annotation expression to flag undefined names in complex types
- **`server.py` hover**: surface annotation type in hover text when hovering an annotated name

---

## Testing

- Lexer: `::` tokenises as `COLONCOLON`; `:` adjacent to `::` (e.g. in slices, dicts) unaffected
- Parser: variable annotation with value, bare annotation, param annotation, return annotation, self-attr annotation, complex type expressions (`list[int]`)
- Transpiler: correct Python output for all annotation forms
- LSP: `AnnotationStatement` does not trigger false-positive undeclared-variable diagnostic
