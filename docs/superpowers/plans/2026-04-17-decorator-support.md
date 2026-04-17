# Decorator Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Python decorator support to L++ using position-based disambiguation — `@expr` before `def`/`class` is a decorator; everywhere else it is a self-attribute reference.

**Architecture:** Four-layer change: AST nodes gain a `decorators` field, the parser detects decorator context via paren-aware lookahead and collects decorator expressions, and the transpiler emits `@decorator` lines before `def`/`class`. All existing `@attr` semantics are unchanged.

**Tech Stack:** Python 3.11, pytest, existing L++ lexer/parser/transpiler/AST stack.

---

### Task 1: Add `decorators` field to AST nodes

**Files:**
- Modify: `src/lpp/ast_nodes.py` (lines 27–43)
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_parser.py` (after existing imports):

```python
def test_functiondef_decorators_default_empty():
    from lpp.ast_nodes import FunctionDef
    node = FunctionDef("foo", [], [], False)
    assert node.decorators == []

def test_classdef_decorators_default_empty():
    from lpp.ast_nodes import ClassDef
    node = ClassDef("Foo", None, [])
    assert node.decorators == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_parser.py::test_functiondef_decorators_default_empty tests/test_parser.py::test_classdef_decorators_default_empty -v
```

Expected: `TypeError` — `FunctionDef` and `ClassDef` don't accept a `decorators` argument yet.

- [ ] **Step 3: Add `decorators` field to both AST nodes**

In `src/lpp/ast_nodes.py`, update `FunctionDef` (line 28):

```python
@dataclass
class FunctionDef:
    name: str
    params: list["Param"]
    body: list[Statement]
    is_method: bool
    decorators: list = field(default_factory=list)
```

Update `ClassDef` (line 40):

```python
@dataclass
class ClassDef:
    name: str
    base: str | None
    body: list[FunctionDef]
    decorators: list = field(default_factory=list)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_parser.py::test_functiondef_decorators_default_empty tests/test_parser.py::test_classdef_decorators_default_empty -v
```

Expected: 2 passed.

- [ ] **Step 5: Run full suite to confirm nothing broken**

```
pytest
```

Expected: all tests pass (the new field has a default, so existing code constructing these nodes without it still works).

- [ ] **Step 6: Commit**

```bash
git add src/lpp/ast_nodes.py tests/test_parser.py
git commit -m "feat(ast): add decorators field to FunctionDef and ClassDef"
```

---

### Task 2: Add `_is_decorator_context()` to parser

**Files:**
- Modify: `src/lpp/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_parser.py`:

```python
def test_is_decorator_context_true_for_simple():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is True

def test_is_decorator_context_true_for_stacked():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@classmethod\n@cache\ndef bar cls\n  1\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is True

def test_is_decorator_context_true_for_class():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@dataclass\nclass Point\n  def @init x\n    @x=x\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is True

def test_is_decorator_context_false_when_no_def_follows():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@x\np(@x)\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is False

def test_is_decorator_context_does_not_advance_position():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.tokens import TokenType
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    p = Parser(tokens)
    pos_before = p.pos
    p._is_decorator_context()
    assert p.pos == pos_before
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_parser.py -k "is_decorator_context" -v
```

Expected: `AttributeError` — method doesn't exist yet.

- [ ] **Step 3: Implement `_is_decorator_context()`**

Add this method to `Parser` in `src/lpp/parser.py`, after `skip_newlines` and before `_parse_string_literal`:

```python
def _is_decorator_context(self) -> bool:
    """Return True if current position starts decorator(s) followed by def/class."""
    save = self.pos
    try:
        while self.peek_type() == TokenType.AT:
            self.advance()  # consume @
            depth = 0
            while not (self.match(TokenType.NEWLINE, TokenType.EOF) and depth == 0):
                if self.peek_type() in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
                    depth += 1
                elif self.peek_type() in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
                    depth -= 1
                self.advance()
            if self.match(TokenType.NEWLINE):
                self.advance()
            self.skip_newlines()
        return self.peek_type() in (TokenType.DEF, TokenType.CLASS)
    finally:
        self.pos = save
```

- [ ] **Step 4: Run to confirm passing**

```
pytest tests/test_parser.py -k "is_decorator_context" -v
```

Expected: 5 passed.

- [ ] **Step 5: Run full suite**

```
pytest
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat(parser): add _is_decorator_context() lookahead"
```

---

### Task 3: Add `_collect_decorators()` to parser

**Files:**
- Modify: `src/lpp/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_parser.py`:

```python
def test_collect_single_decorator():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.ast_nodes import Name
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    p = Parser(tokens)
    decs = p._collect_decorators()
    assert decs == [Name("staticmethod")]

def test_collect_stacked_decorators():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.ast_nodes import Name
    tokens = Lexer("@classmethod\n@cache\ndef bar cls\n  1\n").tokenize()
    p = Parser(tokens)
    decs = p._collect_decorators()
    assert decs == [Name("classmethod"), Name("cache")]

def test_collect_call_decorator():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.ast_nodes import Call, Name, NumberLiteral
    tokens = Lexer("@lru_cache(maxsize=128)\ndef fib n\n  n\n").tokenize()
    p = Parser(tokens)
    decs = p._collect_decorators()
    assert len(decs) == 1
    assert isinstance(decs[0], Call)
    assert decs[0].func == Name("lru_cache")

def test_collect_decorators_advances_past_at_lines():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.tokens import TokenType
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    p = Parser(tokens)
    p._collect_decorators()
    assert p.peek_type() == TokenType.DEF
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_parser.py -k "collect_decorator" -v
```

Expected: `AttributeError` — method doesn't exist yet.

- [ ] **Step 3: Implement `_collect_decorators()`**

Add this method to `Parser` in `src/lpp/parser.py`, immediately after `_is_decorator_context`:

```python
def _collect_decorators(self) -> list:
    """Consume @expr NEWLINE lines and return their expressions."""
    decorators = []
    while self.peek_type() == TokenType.AT:
        self.advance()  # consume @
        expr = self.parse_expression()
        if self.match(TokenType.NEWLINE):
            self.advance()
        self.skip_newlines()
        decorators.append(expr)
    return decorators
```

- [ ] **Step 4: Run to confirm passing**

```
pytest tests/test_parser.py -k "collect_decorator" -v
```

Expected: 4 passed.

- [ ] **Step 5: Run full suite**

```
pytest
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat(parser): add _collect_decorators()"
```

---

### Task 4: Wire decorators into `_parse_statement`, `_parse_function`, `_parse_class`

**Files:**
- Modify: `src/lpp/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_parser.py`:

```python
def test_parse_decorated_function():
    from lpp.ast_nodes import FunctionDef, Name
    node = first("@staticmethod\ndef foo x\n  x\n")
    assert isinstance(node, FunctionDef)
    assert node.name == "foo"
    assert node.decorators == [Name("staticmethod")]

def test_parse_stacked_decorators_on_function():
    from lpp.ast_nodes import FunctionDef, Name
    node = first("@classmethod\n@cache\ndef bar cls\n  1\n")
    assert isinstance(node, FunctionDef)
    assert node.decorators == [Name("classmethod"), Name("cache")]

def test_parse_decorated_class():
    from lpp.ast_nodes import ClassDef, Name
    node = first("@dataclass\nclass Point\n  def @init x\n    @x=x\n")
    assert isinstance(node, ClassDef)
    assert node.name == "Point"
    assert node.decorators == [Name("dataclass")]

def test_parse_decorated_method_inside_class():
    from lpp.ast_nodes import ClassDef, Name
    node = first("class Foo\n  @property\n  def @bar\n    @_bar\n")
    assert isinstance(node, ClassDef)
    assert node.body[0].name == "bar"
    assert node.body[0].decorators == [Name("property")]

def test_at_attr_not_before_def_is_unchanged():
    from lpp.ast_nodes import ExprStatement, SelfAttr
    node = first("@x\n")
    assert isinstance(node, ExprStatement)
    assert node.expr == SelfAttr("x")
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_parser.py -k "decorated" -v
```

Expected: failures — `FunctionDef.decorators` stays empty, decorator lines parsed as `ExprStatement`.

- [ ] **Step 3: Update `_parse_statement` — add decorator guard**

In `src/lpp/parser.py`, update the top of `_parse_statement`:

```python
def _parse_statement(self) -> Statement:
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
    # ... rest of existing dispatch unchanged
```

- [ ] **Step 4: Update `_parse_function` to accept and use `decorators`**

Replace the existing `_parse_function` signature and return statement:

```python
def _parse_function(self, decorators=None) -> FunctionDef:
    if decorators is None:
        decorators = []
    self.expect(TokenType.DEF)
    is_method = self.match(TokenType.AT)
    if is_method:
        self.advance()
    name = self.expect(TokenType.IDENT).value
    params = self._parse_params()
    self.skip_newlines()
    body = self._parse_block()
    return FunctionDef(name, params, body, is_method, decorators)
```

- [ ] **Step 5: Update `_parse_class` to accept `decorators` and handle method decorators**

Replace the existing `_parse_class`:

```python
def _parse_class(self, decorators=None) -> ClassDef:
    if decorators is None:
        decorators = []
    self.expect(TokenType.CLASS)
    name = self.expect(TokenType.IDENT).value
    base = None
    if self.match(TokenType.COLON):
        self.advance()
        base = self.expect(TokenType.IDENT).value
    self.skip_newlines()
    self.expect(TokenType.INDENT)
    methods = []
    self.skip_newlines()
    while not self.match(TokenType.DEDENT, TokenType.EOF):
        method_decorators = []
        if self.peek_type() == TokenType.AT and self._is_decorator_context():
            method_decorators = self._collect_decorators()
        methods.append(self._parse_function(method_decorators))
        self.skip_newlines()
    if self.match(TokenType.DEDENT):
        self.advance()
    return ClassDef(name, base, methods, decorators)
```

- [ ] **Step 6: Run tests to confirm passing**

```
pytest tests/test_parser.py -k "decorated or at_attr" -v
```

Expected: all pass.

- [ ] **Step 7: Run full suite**

```
pytest
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat(parser): wire decorator collection into parse_statement, _parse_function, _parse_class"
```

---

### Task 5: Transpiler — emit decorator lines

**Files:**
- Modify: `src/lpp/transpiler.py` (lines 99–131)
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_transpiler.py`:

```python
def test_decorator_simple_on_fn():
    result = py("@staticmethod\ndef foo x\n  x*2\n")
    assert result == "@staticmethod\ndef foo(x):\n    return x * 2"

def test_decorator_stacked():
    result = py("@classmethod\n@cache\ndef bar cls n\n  n\n")
    assert result == "@classmethod\n@cache\ndef bar(cls, n):\n    return n"

def test_decorator_call_expression():
    result = py("@lru_cache(maxsize=128)\ndef fib n\n  n\n")
    assert result == "@lru_cache(maxsize=128)\ndef fib(n):\n    return n"

def test_decorator_attribute_expression():
    result = py('@app.route("/")\ndef index\n  "hi"\n')
    assert result == '@app.route("/")\ndef index():\n    return "hi"'

def test_decorator_on_class():
    result = py("@dataclass\nclass Point\n  def @init x\n    @x=x\n")
    assert result == "@dataclass\nclass Point:\n    def __init__(self, x):\n        self.x = x"

def test_decorator_on_method():
    result = py("class Foo\n  @property\n  def @bar\n    @_bar\n")
    assert result == "class Foo:\n    @property\n    def bar(self):\n        return self._bar"

def test_no_decorator_unchanged():
    result = py("def foo x\n  x*2\n")
    assert result == "def foo(x):\n    return x * 2"
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_transpiler.py -k "decorator" -v
```

Expected: all fail — decorators not yet emitted.

- [ ] **Step 3: Update `_fn()` to emit decorator lines**

In `src/lpp/transpiler.py`, replace the existing `_fn` method:

```python
def _fn(self, node: FunctionDef, depth: int) -> str:
    pad = INDENT * depth
    lines = []
    for dec in node.decorators:
        lines.append(f"{pad}@{self._expr(dec)}")
    params = []
    if node.is_method:
        params.append("self")
    for p in node.params:
        if p.default is not None:
            params.append(f"{p.name}={self._expr(p.default)}")
        else:
            params.append(p.name)
    param_str = ", ".join(params)
    name = f"__{node.name}__" if node.is_method and node.name in self._DUNDER_NAMES else node.name
    lines.append(f"{pad}def {name}({param_str}):")
    if not node.body:
        lines.append(f"{INDENT * (depth + 1)}pass")
    else:
        *body, last = node.body
        for s in body:
            lines.append(self._stmt(s, depth + 1))
        if isinstance(last, ExprStatement):
            lines.append(f"{INDENT * (depth + 1)}return {self._expr(last.expr)}")
        else:
            lines.append(self._stmt(last, depth + 1))
    return "\n".join(lines)
```

- [ ] **Step 4: Update `_cls()` to emit decorator lines**

In `src/lpp/transpiler.py`, replace the existing `_cls` method:

```python
def _cls(self, node: ClassDef, depth: int) -> str:
    pad = INDENT * depth
    lines = []
    for dec in node.decorators:
        lines.append(f"{pad}@{self._expr(dec)}")
    base = f"({node.base})" if node.base else ""
    lines.append(f"{pad}class {node.name}{base}:")
    for method in node.body:
        lines.append(self._fn(method, depth + 1))
    return "\n".join(lines)
```

- [ ] **Step 5: Run decorator tests**

```
pytest tests/test_transpiler.py -k "decorator" -v
```

Expected: all 7 pass.

- [ ] **Step 6: Run full suite**

```
pytest
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/lpp/transpiler.py tests/test_transpiler.py
git commit -m "feat(transpiler): emit decorator lines before def/class"
```

---

### Task 6: Integration test

**Files:**
- Test: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

Add to `tests/test_integration.py`:

```python
def test_staticmethod_decorator():
    src = textwrap.dedent("""\
        class MathUtils
          @staticmethod
          def add x y
            x+y
        p(MathUtils.add(3,4))
    """)
    assert run_lpp(src) == "7"

def test_property_decorator():
    src = textwrap.dedent("""\
        class Circle
          def @init r
            @r=r
          @property
          def @area
            3.14159*@r*@r
        c=Circle(5)
        p(round(c.area,2))
    """)
    assert run_lpp(src) == "78.54"

def test_class_decorator():
    src = textwrap.dedent("""\
        use dataclasses:dataclass
        @dataclass
        class Point
          def @init x y
            @x=x
            @y=y
        pt=Point(1,2)
        p(pt.x+pt.y)
    """)
    assert run_lpp(src) == "3"
```

- [ ] **Step 2: Run to confirm they pass (no impl needed — already done in Tasks 4+5)**

```
pytest tests/test_integration.py::test_staticmethod_decorator tests/test_integration.py::test_property_decorator tests/test_integration.py::test_class_decorator -v
```

Expected: 3 passed.

- [ ] **Step 3: Run full suite one final time**

```
pytest
```

Expected: all tests pass.

- [ ] **Step 4: Update `priorities.md`**

Add a new entry to `priorities.md`:

```markdown
### 6. Decorator support — `[ DONE ]`
Position-based disambiguation: `@expr` before `def`/`class` = decorator, elsewhere = self-attr.
Supports stacked, call-expression, and attribute decorators. Methods inside classes also supported.
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_integration.py priorities.md
git commit -m "feat: decorator support — integration tests and priorities update"
```
