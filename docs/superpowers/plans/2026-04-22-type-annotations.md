# Type Annotations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `::` type annotation syntax to L++ that transpiles to standard Python type annotations, covering variable declarations, function parameters, return types, and self-attr assignments.

**Architecture:** Add `COLONCOLON` to the lexer, extend existing AST nodes with optional annotation fields plus a new `AnnotationStatement` node for bare declarations, update four parser sites, emit Python-style annotations in the transpiler, and wire `AnnotationStatement` into the semantic scope checker and workspace index.

**Tech Stack:** Python 3.11+, pytest, existing `src/lpp/` package.

---

## File Structure

**Modified:**
- `src/lpp/tokens.py` — add `COLONCOLON` to `TokenType`
- `src/lpp/lexer.py` — add `"::": TokenType.COLONCOLON` to MAP2
- `src/lpp/ast_nodes.py` — add `annotation` to `Param`/`Assignment`, `return_annotation` to `FunctionDef`, new `AnnotationStatement`
- `src/lpp/parser.py` — 5 sites: `_parse_subscript_key`, `_parse_params`, `_parse_function`, `_parse_expr_or_assign`, `_try_parse_self_attr_assign`
- `src/lpp/transpiler.py` — `_fn`, `Assignment` case, new `AnnotationStatement` case
- `src/lpp/semantic.py` — `_collect_decls` and `_check_stmt` for `AnnotationStatement`
- `src/lpp/index.py` — `_extract_symbols` for `AnnotationStatement`

**Tests:**
- `tests/test_lexer.py`
- `tests/test_parser.py`
- `tests/test_transpiler.py`

---

### Task 1: COLONCOLON Token

**Files:**
- Modify: `src/lpp/tokens.py`
- Modify: `src/lpp/lexer.py`
- Test: `tests/test_lexer.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_lexer.py`:

```python
def test_coloncolon_token():
    assert types("::") == [TokenType.COLONCOLON]

def test_coloncolon_is_one_token():
    toks = [t for t in tokenize("::") if t.type != TokenType.EOF]
    assert len(toks) == 1

def test_single_colon_unchanged():
    assert types(":") == [TokenType.COLON]
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_lexer.py::test_coloncolon_token -v
```
Expected: `AttributeError: COLONCOLON`

- [ ] **Step 3: Add COLONCOLON to TokenType**

In `src/lpp/tokens.py`, add after `YIELD = auto()` (still inside the `TokenType` class):

```python
COLONCOLON = auto()  # ::
```

- [ ] **Step 4: Add `::` to MAP2 in the lexer**

In `src/lpp/lexer.py`, update `MAP2` to include:

```python
MAP2 = {
    "->": TokenType.ARROW, "<<": TokenType.APPEND,
    "==": TokenType.EQEQ, "!=": TokenType.NEQ,
    "<=": TokenType.LTE,  ">=": TokenType.GTE,
    "+=": TokenType.PLUSEQ, "-=": TokenType.MINUSEQ,
    "*=": TokenType.STAREQ, "/=": TokenType.SLASHEQ,
    "**": TokenType.STARSTAR, "//": TokenType.DOUBLESLASH,
    "%=": TokenType.PERCENTEQ,
    "::": TokenType.COLONCOLON,
}
```

- [ ] **Step 5: Run all lexer tests**

```
pytest tests/test_lexer.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/lpp/tokens.py src/lpp/lexer.py tests/test_lexer.py
git commit -m "feat(lexer): add COLONCOLON token for :: type annotation operator"
```

---

### Task 2: AST Node Additions

**Files:**
- Modify: `src/lpp/ast_nodes.py`

- [ ] **Step 1: Add `annotation` field to `Param`**

In `src/lpp/ast_nodes.py`, update `Param` to:

```python
@dataclass
class Param:
    name: str
    default: Expression | None = None
    kind: str = "pos"
    annotation: Expression | None = None
```

- [ ] **Step 2: Add `annotation` field to `Assignment`**

Update `Assignment` to:

```python
@dataclass
class Assignment:
    target: str | Expression
    value: Expression
    annotation: Expression | None = None
    line: int | None = None
```

- [ ] **Step 3: Add `return_annotation` field to `FunctionDef`**

Update `FunctionDef` to:

```python
@dataclass
class FunctionDef:
    name: str
    params: list["Param"]
    body: list[Statement]
    is_method: bool
    decorators: list = field(default_factory=list)
    return_annotation: "Expression | None" = None
    line: int | None = None
```

- [ ] **Step 4: Add `AnnotationStatement` node**

After `YieldStatement`, add:

```python
@dataclass
class AnnotationStatement:
    target: str | Expression
    annotation: Expression
    line: int | None = None
```

- [ ] **Step 5: Add `AnnotationStatement` to the `Statement` union**

Update the `Statement` union at the top of the file:

```python
Statement = Union[
    "FunctionDef", "ClassDef", "Assignment", "AugAssignment",
    "IfStatement", "ForStatement", "DoStatement", "TryStatement",
    "RetStatement", "UseStatement", "AliasStatement",
    "AppendStatement", "ExprStatement",
    "BreakStatement", "ContinueStatement", "RaiseStatement",
    "WithStatement", "GlobalStatement", "NonlocalStatement",
    "UnpackAssignment", "AssertStatement", "DelStatement", "PassStatement",
    "YieldStatement", "AnnotationStatement",
]
```

- [ ] **Step 6: Verify existing tests still pass**

```
pytest tests/ -v
```
Expected: all existing tests pass (new fields have `None` defaults, no breakage)

- [ ] **Step 7: Commit**

```bash
git add src/lpp/ast_nodes.py
git commit -m "feat(ast): add annotation fields and AnnotationStatement node"
```

---

### Task 3: Subscript Comma Support (multi-param generics)

**Files:**
- Modify: `src/lpp/parser.py`
- Test: `tests/test_parser.py`

This is required so `dict[str, int]`, `Union[str, int]`, etc. work as type expressions.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_parser.py`:

```python
def test_subscript_multi_arg():
    # dict[str, int] — comma inside [] produces Tuple key
    result = parse_expr("dict[str, int]")
    assert result == Subscript(Name("dict"), Tuple([Name("str"), Name("int")]))
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_parser.py::test_subscript_multi_arg -v
```
Expected: `FAIL` — `ParseError: expected RBRACKET, got COMMA`

- [ ] **Step 3: Update `_parse_subscript_key` to handle comma-separated keys**

In `src/lpp/parser.py`, replace `_parse_subscript_key`:

```python
def _parse_subscript_key(self) -> Expression:
    if self.match(TokenType.COLON):
        start = None
    else:
        start = self.parse_expression()
    if not self.match(TokenType.COLON):
        # Comma-separated tuple key: dict[str, int]
        if self.match(TokenType.COMMA):
            elements = [start]
            while self.match(TokenType.COMMA):
                self.advance()
                if self.match(TokenType.RBRACKET):
                    break
                elements.append(self.parse_expression())
            self.expect(TokenType.RBRACKET)
            return Tuple(elements)
        self.expect(TokenType.RBRACKET)
        return start
    self.advance()
    stop = None if self.match(TokenType.COLON, TokenType.RBRACKET) else self.parse_expression()
    step = None
    if self.match(TokenType.COLON):
        self.advance()
        step = None if self.match(TokenType.RBRACKET) else self.parse_expression()
    self.expect(TokenType.RBRACKET)
    return Slice(start, stop, step)
```

- [ ] **Step 4: Run all parser tests**

```
pytest tests/test_parser.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat(parser): support comma-separated subscript keys for generic type expressions"
```

---

### Task 4: Parser — Param + Return Type Annotations

**Files:**
- Modify: `src/lpp/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_parser.py`:

```python
def parse_stmts(src: str):
    tokens = Lexer(src).tokenize()
    return Parser(tokens).parse().body

def test_param_annotation_simple():
    stmts = parse_stmts("def f(x::int)\n    x\n")
    assert stmts[0].params[0].annotation == Name("int")

def test_param_annotation_complex():
    stmts = parse_stmts("def f(items::list[int])\n    items\n")
    assert stmts[0].params[0].annotation == Subscript(Name("list"), Name("int"))

def test_return_annotation():
    stmts = parse_stmts("def f()::bool\n    True\n")
    assert stmts[0].return_annotation == Name("bool")

def test_param_and_return_annotation():
    stmts = parse_stmts("def f(x::int)::str\n    s(x)\n")
    fn = stmts[0]
    assert fn.params[0].annotation == Name("int")
    assert fn.return_annotation == Name("str")

def test_param_no_annotation_unchanged():
    stmts = parse_stmts("def f(x)\n    x\n")
    assert stmts[0].params[0].annotation is None
    assert stmts[0].return_annotation is None
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_parser.py::test_param_annotation_simple tests/test_parser.py::test_return_annotation -v
```
Expected: `FAIL` — `AssertionError: None != Name('int')`

- [ ] **Step 3: Update `_parse_params` to handle `::` annotation**

In `src/lpp/parser.py`, replace `_parse_params`:

```python
def _parse_params(self) -> list[Param]:
    params = []
    while self.match(TokenType.IDENT, TokenType.STAR, TokenType.STARSTAR):
        if self.match(TokenType.STARSTAR):
            self.advance()
            pname = self.expect(TokenType.IDENT).value
            annotation = None
            if self.match(TokenType.COLONCOLON):
                self.advance()
                annotation = self.parse_expression()
            params.append(Param(pname, kind="kw", annotation=annotation))
        elif self.match(TokenType.STAR):
            self.advance()
            pname = self.expect(TokenType.IDENT).value
            annotation = None
            if self.match(TokenType.COLONCOLON):
                self.advance()
                annotation = self.parse_expression()
            params.append(Param(pname, kind="var", annotation=annotation))
        else:
            pname = self.advance().value
            annotation = None
            if self.match(TokenType.COLONCOLON):
                self.advance()
                annotation = self.parse_expression()
            default = None
            if self.match(TokenType.EQ):
                self.advance()
                default = self.parse_expression()
            params.append(Param(pname, default, annotation=annotation))
    return params
```

- [ ] **Step 4: Update `_parse_function` to handle `::` return annotation**

In `_parse_function`, after `params = self._parse_params()`, add:

```python
return_annotation = None
if self.match(TokenType.COLONCOLON):
    self.advance()
    return_annotation = self.parse_expression()
```

Then update the final `return` line to:

```python
return FunctionDef(name, params, body, is_method, decorators, return_annotation)
```

- [ ] **Step 5: Run all parser tests**

```
pytest tests/test_parser.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat(parser): add :: annotation support for params and return types"
```

---

### Task 5: Parser — Variable Annotations

**Files:**
- Modify: `src/lpp/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_parser.py`:

```python
def test_annotated_assignment():
    stmts = parse_stmts("x::int = 5\n")
    stmt = stmts[0]
    assert isinstance(stmt, Assignment)
    assert stmt.target == "x"
    assert stmt.annotation == Name("int")
    assert stmt.value == NumberLiteral(5)

def test_bare_annotation_statement():
    stmts = parse_stmts("x::int\n")
    stmt = stmts[0]
    assert isinstance(stmt, AnnotationStatement)
    assert stmt.target == "x"
    assert stmt.annotation == Name("int")

def test_annotated_complex_type():
    stmts = parse_stmts("items::list[str] = []\n")
    stmt = stmts[0]
    assert isinstance(stmt, Assignment)
    assert stmt.annotation == Subscript(Name("list"), Name("str"))

def test_annotated_dict_type():
    stmts = parse_stmts("mapping::dict[str, int] = {}\n")
    stmt = stmts[0]
    assert isinstance(stmt, Assignment)
    assert stmt.annotation == Subscript(Name("dict"), Tuple([Name("str"), Name("int")]))
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_parser.py::test_annotated_assignment tests/test_parser.py::test_bare_annotation_statement -v
```
Expected: `FAIL` — `AssertionError: None != Name('int')` (annotation not parsed)

- [ ] **Step 3: Add `::` handling to `_parse_expr_or_assign` Path 3**

In `_parse_expr_or_assign`, after `expr = self.parse_expression()` and before the `AUG = {...}` dict, insert:

```python
# Type annotation: x::type = val  OR  x::type (bare declaration)
if self.peek_type() == TokenType.COLONCOLON:
    self.advance()
    annotation = self.parse_expression()
    if self.peek_type() == TokenType.EQ:
        self.advance()
        value = self._parse_stmt_tuple()
        if self.match(TokenType.NEWLINE): self.advance()
        target = expr.id if isinstance(expr, Name) else expr
        return Assignment(target, value, annotation=annotation)
    if self.match(TokenType.NEWLINE): self.advance()
    target = expr.id if isinstance(expr, Name) else expr
    return AnnotationStatement(target, annotation)
```

- [ ] **Step 4: Run all parser tests**

```
pytest tests/test_parser.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat(parser): add :: annotation support for variable declarations"
```

---

### Task 6: Parser — Self-Attr Annotations

**Files:**
- Modify: `src/lpp/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_parser.py`:

```python
def test_self_attr_annotated_assignment():
    stmts = parse_stmts("@name::str = \"Alice\"\n")
    stmt = stmts[0]
    assert isinstance(stmt, Assignment)
    assert stmt.target == "self.name"
    assert stmt.annotation == Name("str")
    assert stmt.value == StringLiteral(["Alice"])

def test_self_attr_bare_annotation():
    stmts = parse_stmts("@count::int\n")
    stmt = stmts[0]
    assert isinstance(stmt, AnnotationStatement)
    assert stmt.target == "self.count"
    assert stmt.annotation == Name("int")
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_parser.py::test_self_attr_annotated_assignment tests/test_parser.py::test_self_attr_bare_annotation -v
```
Expected: `FAIL` — annotation is `None` / not an `AnnotationStatement`

- [ ] **Step 3: Update `_try_parse_self_attr_assign`**

Replace the entire `_try_parse_self_attr_assign` method in `src/lpp/parser.py`:

```python
def _try_parse_self_attr_assign(self) -> Statement | None:
    """Try to parse @attr = expr, @attr op= expr, @attr::type = expr, or @attr::type."""
    save = self.pos
    try:
        self.advance()  # consume @
        attr = self.expect(TokenType.IDENT).value
        annotation = None
        if self.peek_type() == TokenType.COLONCOLON:
            self.advance()
            annotation = self.parse_expression()
        AUG = {
            TokenType.PLUSEQ: "+=", TokenType.MINUSEQ: "-=",
            TokenType.STAREQ: "*=", TokenType.SLASHEQ: "/=", TokenType.PERCENTEQ: "%=",
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
            return Assignment(f"self.{attr}", value, annotation=annotation)
        if annotation is not None:
            if self.match(TokenType.NEWLINE): self.advance()
            return AnnotationStatement(f"self.{attr}", annotation)
        self.pos = save
        return None
    except ParseError:
        self.pos = save
        return None
```

- [ ] **Step 4: Run all parser tests**

```
pytest tests/test_parser.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat(parser): add :: annotation support for self-attr declarations"
```

---

### Task 7: Transpiler — Param + Return Type Annotations

**Files:**
- Modify: `src/lpp/transpiler.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_transpiler.py`:

```python
def test_annotated_param():
    assert py("def f(x::int)\n    x\n") == "def f(x: int):\n    return x"

def test_return_annotation():
    assert py("def f()::bool\n    True\n") == "def f() -> bool:\n    return True"

def test_param_and_return_annotation():
    result = py("def f(x::int, y::str)::bool\n    True\n")
    assert result == "def f(x: int, y: str) -> bool:\n    return True"

def test_annotated_param_with_default():
    result = py("def f(x::int = 0)\n    x\n")
    assert result == "def f(x: int = 0):\n    return x"

def test_annotated_varargs():
    result = py("def f(*args::int)\n    args\n")
    assert result == "def f(*args: int):\n    return args"
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_transpiler.py::test_annotated_param tests/test_transpiler.py::test_return_annotation -v
```
Expected: `FAIL` — param emits `x` instead of `x: int`, no `-> bool` suffix

- [ ] **Step 3: Update the param-building loop in `_fn`**

In `src/lpp/transpiler.py`, update the `for p in node.params:` loop inside `_fn`:

```python
for p in node.params:
    ann = f": {self._expr(p.annotation)}" if p.annotation is not None else ""
    if p.kind == "var":
        params.append(f"*{p.name}{ann}")
    elif p.kind == "kw":
        params.append(f"**{p.name}{ann}")
    elif p.default is not None:
        # PEP 8: spaces around = when annotation present, no spaces otherwise
        sep = " = " if p.annotation is not None else "="
        params.append(f"{p.name}{ann}{sep}{self._expr(p.default)}")
    else:
        params.append(f"{p.name}{ann}")
```

- [ ] **Step 4: Add return annotation to the `def` line in `_fn`**

Replace the line:

```python
lines.append(f"{pad}def {name}({param_str}):")
```

With:

```python
ret_ann = f" -> {self._expr(node.return_annotation)}" if node.return_annotation is not None else ""
lines.append(f"{pad}def {name}({param_str}){ret_ann}:")
```

- [ ] **Step 5: Run all transpiler tests**

```
pytest tests/test_transpiler.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/lpp/transpiler.py tests/test_transpiler.py
git commit -m "feat(transpiler): emit Python annotations for params and return types"
```

---

### Task 8: Transpiler — Variable Annotation + AnnotationStatement

**Files:**
- Modify: `src/lpp/transpiler.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_transpiler.py`:

```python
def test_annotated_variable():
    assert py("x::int = 5\n") == "x: int = 5"

def test_bare_annotation():
    assert py("x::int\n") == "x: int"

def test_annotated_complex_type():
    assert py("items::list[str] = []\n") == "items: list[str] = []"

def test_annotated_dict_type():
    assert py("mapping::dict[str, int] = {}\n") == "mapping: dict[str, int] = {}"

def test_self_attr_annotated_assignment():
    result = py("def @init()\n    @name::str = \"hi\"\n")
    assert "self.name: str = \"hi\"" in result

def test_self_attr_bare_annotation():
    result = py("def @init()\n    @count::int\n")
    assert "self.count: int" in result
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_transpiler.py::test_annotated_variable tests/test_transpiler.py::test_bare_annotation -v
```
Expected: `FAIL` — `x: int = 5` emits as `x = 5` (annotation ignored); bare `AnnotationStatement` causes a transpiler error (no match arm)

- [ ] **Step 3: Update the `Assignment` case in `_emit_stmt` to emit annotation**

In `src/lpp/transpiler.py`, update the `case Assignment(target, value):` block:

```python
case Assignment(target, value):
    tgt = target if isinstance(target, str) else self._expr(target)
    if node.annotation is not None:
        return f"{pad}{tgt}: {self._expr(node.annotation)} = {self._expr(value)}"
    return f"{pad}{tgt} = {self._expr(value)}"
```

- [ ] **Step 4: Add `AnnotationStatement` case to `_emit_stmt`**

After the `Assignment` case block, add:

```python
case AnnotationStatement(target, annotation):
    tgt = target if isinstance(target, str) else self._expr(target)
    return f"{pad}{tgt}: {self._expr(annotation)}"
```

- [ ] **Step 5: Run all transpiler tests**

```
pytest tests/test_transpiler.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/lpp/transpiler.py tests/test_transpiler.py
git commit -m "feat(transpiler): emit Python annotations for variables and bare declarations"
```

---

### Task 9: Semantic Scope + Workspace Index

**Files:**
- Modify: `src/lpp/semantic.py`
- Modify: `src/lpp/index.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_transpiler.py`:

```python
def test_annotation_defines_name_in_scope():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.semantic import check_names
    src = "x::int\nx = 5\n"
    tree = Parser(Lexer(src).tokenize()).parse()
    errors = check_names(tree)
    assert errors == [], f"Unexpected undeclared-name errors: {errors}"

def test_annotation_annotation_expr_checked():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.semantic import check_names
    # MyType is not declared — should produce an error
    src = "x::MyType\n"
    tree = Parser(Lexer(src).tokenize()).parse()
    errors = check_names(tree)
    assert any(name == "MyType" for name, _ in errors)
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_transpiler.py::test_annotation_defines_name_in_scope -v
```
Expected: `FAIL` — `x` is treated as undeclared on the second line because `AnnotationStatement` is not recognized in `_collect_decls`

- [ ] **Step 3: Add `AnnotationStatement` to semantic.py imports**

In `src/lpp/semantic.py`, add `AnnotationStatement` to the import block:

```python
from .ast_nodes import (
    Program, Statement, Expression,
    FunctionDef, ClassDef, Assignment, AugAssignment, AppendStatement,
    ForStatement, IfStatement, DoStatement, TryStatement, WithStatement,
    UnpackAssignment, AliasStatement, UseStatement,
    ExprStatement, RetStatement, RaiseStatement, AssertStatement,
    GlobalStatement, NonlocalStatement, YieldStatement, DelStatement,
    AnnotationStatement,
    Name, SelfAttr, Attribute, Subscript, BinOp, UnaryOp, Call,
    ZeroArgCall, Pipeline, Lambda, Compose, StringLiteral, NumberLiteral,
    ListLiteral, DictLiteral, TernaryOp, Spread, ListComp, DictComp,
    SetComp, Tuple, Slice, SetLiteral, ChainedComparison,
)
```

- [ ] **Step 4: Update `_collect_decls` to register `AnnotationStatement` targets**

In `_collect_decls`, after the `UnpackAssignment` block, add:

```python
elif isinstance(stmt, AnnotationStatement) and isinstance(stmt.target, str):
    into.add(stmt.target)
```

- [ ] **Step 5: Update `_check_stmt` to walk `AnnotationStatement`**

In `_check_stmt`, after the `YieldStatement` block, add:

```python
elif isinstance(stmt, AnnotationStatement):
    _check_expr(stmt.annotation, scope, line, errors)
```

- [ ] **Step 6: Update `index.py` to index annotated declarations**

In `src/lpp/index.py`, update the import and `_extract_symbols`:

```python
from .ast_nodes import Program, FunctionDef, ClassDef, Assignment, AnnotationStatement

def _extract_symbols(tree: Program, uri: str) -> list[Symbol]:
    symbols = []
    for node in tree.body:
        if isinstance(node, FunctionDef):
            symbols.append(Symbol(node.name, "function", uri, node.line or 1))
        elif isinstance(node, ClassDef):
            symbols.append(Symbol(node.name, "class", uri, node.line or 1))
        elif isinstance(node, Assignment) and isinstance(node.target, str):
            symbols.append(Symbol(node.target, "variable", uri, node.line or 1))
        elif isinstance(node, AnnotationStatement) and isinstance(node.target, str):
            symbols.append(Symbol(node.target, "variable", uri, node.line or 1))
    return symbols
```

- [ ] **Step 7: Run the full test suite**

```
pytest tests/ -v
```
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add src/lpp/semantic.py src/lpp/index.py tests/test_transpiler.py
git commit -m "feat(semantic): recognize AnnotationStatement in scope checker and workspace index"
```
