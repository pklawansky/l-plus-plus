# L++ Transpiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-based L++ → Python transpiler that accepts `.lpp` source files and emits valid, executable Python.

**Architecture:** Hand-rolled recursive descent parser produces an AST from L++ source; a separate transpiler walks the AST and emits Python strings. The prelude (standard aliases) is injected automatically at the top of every output file. A CLI ties it together.

**Tech Stack:** Python 3.11+, pytest, dataclasses, no external parser dependencies.

---

## File Structure

```
l-plus-plus/
  src/
    lpp/
      __init__.py         # package init, exposes compile_lpp()
      tokens.py           # TokenType enum + Token dataclass
      lexer.py            # L++ source → token stream
      ast_nodes.py        # all AST node dataclasses
      parser.py           # token stream → AST
      transpiler.py       # AST → Python source string
      prelude.py          # standard alias map + injection logic
      cli.py              # `lpp` command entry point
  tests/
    conftest.py           # shared fixtures
    test_lexer.py
    test_parser.py
    test_transpiler.py
    test_prelude.py
    test_integration.py
  pyproject.toml
```

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `src/lpp/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "lpp"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
lpp = "lpp.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create package init**

```python
# src/lpp/__init__.py
from .lexer import Lexer
from .parser import Parser
from .transpiler import Transpiler

def compile_lpp(source: str) -> str:
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    return Transpiler().transpile(ast)
```

- [ ] **Step 3: Create test conftest**

```python
# tests/conftest.py
import pytest
from lpp import compile_lpp

def lpp(source: str) -> str:
    """Compile L++ source and return Python string."""
    return compile_lpp(source)
```

- [ ] **Step 4: Install in editable mode**

Run: `pip install -e .`
Expected: package `lpp` importable from `src/lpp`

- [ ] **Step 5: Verify pytest discovers tests**

Run: `pytest --collect-only`
Expected: no errors (zero tests collected is fine at this stage)

- [ ] **Step 6: Commit**

```bash
git init
git add pyproject.toml src/ tests/
git commit -m "feat: project scaffold"
```

---

## Task 2: Token Definitions

**Files:**
- Create: `src/lpp/tokens.py`
- Create: `tests/test_lexer.py` (stub)

- [ ] **Step 1: Write token stub test**

```python
# tests/test_lexer.py
from lpp.tokens import TokenType, Token

def test_token_creation():
    t = Token(TokenType.IDENT, "foo", line=1)
    assert t.type == TokenType.IDENT
    assert t.value == "foo"
    assert t.line == 1
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_lexer.py::test_token_creation -v`
Expected: FAIL — `ModuleNotFoundError: lpp.tokens`

- [ ] **Step 3: Implement tokens.py**

```python
# src/lpp/tokens.py
from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    # Keywords
    FN = auto(); CLS = auto(); IF = auto(); EL = auto()
    FOR = auto(); IN = auto(); DO = auto(); RET = auto()
    TRY = auto(); ERR = auto(); AS = auto()
    USE = auto(); ALIAS = auto()
    # Literals
    NUMBER = auto(); STRING = auto(); IDENT = auto()
    # Operators
    PIPE = auto()       # |
    ARROW = auto()      # ->
    AT = auto()         # @
    BANG = auto()       # !
    TILDE = auto()      # ~
    AMP = auto()        # &
    APPEND = auto()     # <<
    COLON = auto()      # :
    COLONCOLON = auto() # :: (module:item separator in use)
    # Arithmetic / comparison
    PLUS = auto(); MINUS = auto(); STAR = auto()
    SLASH = auto(); PERCENT = auto()
    EQ = auto(); EQEQ = auto(); NEQ = auto()
    LT = auto(); GT = auto(); LTE = auto(); GTE = auto()
    PLUSEQ = auto(); MINUSEQ = auto(); STAREQ = auto(); SLASHEQ = auto()
    # Delimiters
    LPAREN = auto(); RPAREN = auto()
    LBRACKET = auto(); RBRACKET = auto()
    LBRACE = auto(); RBRACE = auto()
    COMMA = auto(); DOT = auto()
    # Structural
    NEWLINE = auto(); INDENT = auto(); DEDENT = auto(); EOF = auto()

KEYWORDS: dict[str, TokenType] = {
    "fn": TokenType.FN,
    "cls": TokenType.CLS,
    "if": TokenType.IF,
    "el": TokenType.EL,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "do": TokenType.DO,
    "ret": TokenType.RET,
    "try": TokenType.TRY,
    "err": TokenType.ERR,
    "as": TokenType.AS,
    "use": TokenType.USE,
    "alias": TokenType.ALIAS,
}

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
```

- [ ] **Step 4: Run test to confirm pass**

Run: `pytest tests/test_lexer.py::test_token_creation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lpp/tokens.py tests/test_lexer.py
git commit -m "feat: token definitions"
```

---

## Task 3: AST Node Definitions

**Files:**
- Create: `src/lpp/ast_nodes.py`
- Create: `tests/test_parser.py` (stub)

- [ ] **Step 1: Write AST stub test**

```python
# tests/test_parser.py
from lpp.ast_nodes import FunctionDef, Param, Name, NumberLiteral

def test_ast_nodes_instantiate():
    node = FunctionDef(
        name="add",
        params=[Param("x"), Param("y")],
        body=[Name("x")],
        is_method=False,
    )
    assert node.name == "add"
    assert len(node.params) == 2
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_parser.py::test_ast_nodes_instantiate -v`
Expected: FAIL — `ModuleNotFoundError: lpp.ast_nodes`

- [ ] **Step 3: Implement ast_nodes.py**

```python
# src/lpp/ast_nodes.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Union

Expression = Union[
    "BinOp", "UnaryOp", "Call", "ZeroArgCall", "Pipeline",
    "Lambda", "Name", "SelfAttr", "Attribute", "Subscript",
    "StringLiteral", "NumberLiteral", "ListLiteral", "DictLiteral",
    "TernaryOp", "Spread",
]
Statement = Union[
    "FunctionDef", "ClassDef", "Assignment", "AugAssignment",
    "IfStatement", "ForStatement", "DoStatement", "TryStatement",
    "RetStatement", "UseStatement", "AliasStatement",
    "AppendStatement", "ExprStatement",
]

@dataclass
class Program:
    body: list[Statement]

# --- Statements ---

@dataclass
class FunctionDef:
    name: str          # bare name; @ prefix stripped, is_method=True
    params: list["Param"]
    body: list[Statement]
    is_method: bool

@dataclass
class Param:
    name: str
    default: Expression | None = None

@dataclass
class ClassDef:
    name: str
    base: str | None
    body: list[FunctionDef]

@dataclass
class Assignment:
    target: str
    value: Expression

@dataclass
class AugAssignment:
    target: str
    op: str            # +=, -=, *=, /=
    value: Expression

@dataclass
class AppendStatement:
    target: Expression
    value: Expression

@dataclass
class IfStatement:
    condition: Expression
    body: list[Statement]
    elifs: list[tuple[Expression | None, list[Statement]]] = field(default_factory=list)
    # elifs[-1] has condition=None when the last branch is a bare `el`

@dataclass
class ForStatement:
    targets: list[str]
    iterable: Expression
    body: list[Statement]

@dataclass
class DoStatement:
    condition: Expression
    body: list[Statement]

@dataclass
class TryStatement:
    body: list[Statement]
    handlers: list["ErrHandler"]

@dataclass
class ErrHandler:
    exc_type: str | None
    name: str | None
    body: list[Statement]

@dataclass
class RetStatement:
    value: Expression | None

@dataclass
class UseStatement:
    imports: list["UseImport"]

@dataclass
class UseImport:
    module: str
    item: str | None = None    # None = import whole module
    alias: str | None = None   # None = no alias

@dataclass
class AliasStatement:
    name: str
    target: Expression

@dataclass
class ExprStatement:
    expr: Expression

# --- Expressions ---

@dataclass
class BinOp:
    left: Expression
    op: str
    right: Expression

@dataclass
class UnaryOp:
    op: str
    operand: Expression

@dataclass
class Call:
    func: Expression
    args: list[Expression] = field(default_factory=list)
    kwargs: dict[str, Expression] = field(default_factory=dict)

@dataclass
class ZeroArgCall:
    func: Expression

@dataclass
class Pipeline:
    steps: list[Expression]

@dataclass
class Lambda:
    params: list[str]
    body: Expression

@dataclass
class Name:
    id: str

@dataclass
class SelfAttr:
    attr: str          # @name → self.name

@dataclass
class Attribute:
    obj: Expression
    attr: str

@dataclass
class Subscript:
    obj: Expression
    key: Expression

@dataclass
class StringLiteral:
    parts: list[str | Expression]   # alternating raw str and Expression

@dataclass
class NumberLiteral:
    value: int | float

@dataclass
class ListLiteral:
    elements: list[Expression]

@dataclass
class DictLiteral:
    pairs: list[tuple[Expression, Expression]]

@dataclass
class TernaryOp:
    value: Expression
    condition: Expression
    else_value: Expression

@dataclass
class Spread:
    value: Expression
```

- [ ] **Step 4: Run test to confirm pass**

Run: `pytest tests/test_parser.py::test_ast_nodes_instantiate -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lpp/ast_nodes.py tests/test_parser.py
git commit -m "feat: AST node definitions"
```

---

## Task 4: Lexer

**Files:**
- Create: `src/lpp/lexer.py`
- Modify: `tests/test_lexer.py`

- [ ] **Step 1: Write lexer tests**

```python
# tests/test_lexer.py  (replace existing stub)
import pytest
from lpp.tokens import TokenType, Token
from lpp.lexer import Lexer

def tokenize(src: str) -> list[Token]:
    return Lexer(src).tokenize()

def types(src: str) -> list[TokenType]:
    return [t.type for t in tokenize(src) if t.type != TokenType.EOF]

def test_token_creation():
    t = Token(TokenType.IDENT, "foo", line=1)
    assert t.type == TokenType.IDENT

def test_keywords():
    assert types("fn") == [TokenType.FN]
    assert types("if el for in do ret try err use alias cls as") == [
        TokenType.IF, TokenType.EL, TokenType.FOR, TokenType.IN,
        TokenType.DO, TokenType.RET, TokenType.TRY, TokenType.ERR,
        TokenType.USE, TokenType.ALIAS, TokenType.CLS, TokenType.AS,
        # fn already covered, but include for completeness:
    ][:12]

def test_identifiers():
    assert types("foo bar x y1") == [TokenType.IDENT] * 4

def test_numbers():
    toks = tokenize("42 3.14")
    assert toks[0].type == TokenType.NUMBER and toks[0].value == "42"
    assert toks[1].type == TokenType.NUMBER and toks[1].value == "3.14"

def test_string_literal():
    toks = tokenize('"hello world"')
    assert toks[0].type == TokenType.STRING
    assert toks[0].value == "hello world"

def test_operators():
    assert types("| -> @ ! ~ & <<") == [
        TokenType.PIPE, TokenType.ARROW, TokenType.AT,
        TokenType.BANG, TokenType.TILDE, TokenType.AMP, TokenType.APPEND,
    ]

def test_comparison_ops():
    assert types("== != < > <= >=") == [
        TokenType.EQEQ, TokenType.NEQ, TokenType.LT,
        TokenType.GT, TokenType.LTE, TokenType.GTE,
    ]

def test_indent_dedent():
    src = "fn foo\n  x\n"
    toks = tokenize(src)
    tt = [t.type for t in toks]
    assert TokenType.INDENT in tt
    assert TokenType.DEDENT in tt

def test_comments_stripped():
    assert types("x=1 # a comment\ny=2") == [
        TokenType.IDENT, TokenType.EQ, TokenType.NUMBER,
        TokenType.NEWLINE,
        TokenType.IDENT, TokenType.EQ, TokenType.NUMBER,
    ]

def test_string_with_interpolation_markers():
    toks = tokenize('"hello $name$!"')
    assert toks[0].type == TokenType.STRING
    # raw value preserved including $ markers — parser handles interpolation
    assert "$name$" in toks[0].value
```

- [ ] **Step 2: Run to confirm failures**

Run: `pytest tests/test_lexer.py -v`
Expected: multiple FAILs — `ModuleNotFoundError: lpp.lexer`

- [ ] **Step 3: Implement lexer.py**

```python
# src/lpp/lexer.py
from .tokens import Token, TokenType, KEYWORDS

class LexError(Exception):
    pass

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.tokens: list[Token] = []
        self.indent_stack: list[int] = [0]

    def peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else ""

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def add(self, type: TokenType, value: str = "") -> None:
        self.tokens.append(Token(type, value, self.line))

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.source):
            self._scan_line()
        # Close any open indents
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.add(TokenType.DEDENT)
        self.add(TokenType.EOF)
        return self.tokens

    def _scan_line(self) -> None:
        # Measure indent at start of line
        indent = 0
        while self.peek() == " ":
            indent += 1
            self.pos += 1

        # Blank line or comment-only line — skip without emitting NEWLINE
        if self.peek() in ("", "\n", "#"):
            while self.peek() not in ("", "\n"):
                self.pos += 1
            if self.peek() == "\n":
                self.pos += 1
                self.line += 1
            return

        # Handle indent/dedent
        current = self.indent_stack[-1]
        if indent > current:
            self.indent_stack.append(indent)
            self.add(TokenType.INDENT)
        elif indent < current:
            while self.indent_stack[-1] > indent:
                self.indent_stack.pop()
                self.add(TokenType.DEDENT)

        # Scan tokens on this line
        while self.peek() not in ("", "\n"):
            self._scan_token()

        self.add(TokenType.NEWLINE)
        if self.peek() == "\n":
            self.pos += 1
            self.line += 1

    def _scan_token(self) -> None:
        ch = self.peek()

        if ch == " ":
            self.pos += 1
            return

        if ch == "#":
            while self.peek() not in ("", "\n"):
                self.pos += 1
            return

        if ch == '"':
            self._scan_string()
            return

        if ch.isdigit() or (ch == "-" and self.peek(1).isdigit() and
                            (not self.tokens or
                             self.tokens[-1].type in (TokenType.EQ, TokenType.LPAREN,
                                                       TokenType.COMMA, TokenType.NEWLINE,
                                                       TokenType.INDENT))):
            self._scan_number()
            return

        if ch.isalpha() or ch == "_":
            self._scan_word()
            return

        self._scan_operator()

    def _scan_string(self) -> None:
        self.pos += 1  # skip opening "
        value = ""
        while self.peek() not in ('"', "", "\n"):
            if self.peek() == "\\":
                self.pos += 1
                esc = self.advance()
                value += {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc)
            else:
                value += self.advance()
        if self.peek() == '"':
            self.pos += 1
        self.add(TokenType.STRING, value)

    def _scan_number(self) -> None:
        start = self.pos
        if self.peek() == "-":
            self.pos += 1
        while self.peek().isdigit():
            self.pos += 1
        if self.peek() == "." and self.peek(1).isdigit():
            self.pos += 1
            while self.peek().isdigit():
                self.pos += 1
        self.add(TokenType.NUMBER, self.source[start:self.pos])

    def _scan_word(self) -> None:
        start = self.pos
        while self.peek().isalnum() or self.peek() == "_":
            self.pos += 1
        word = self.source[start:self.pos]
        tt = KEYWORDS.get(word, TokenType.IDENT)
        self.add(tt, word)

    def _scan_operator(self) -> None:
        ch = self.advance()
        two = ch + self.peek()
        three = two + self.peek(1) if len(two) == 2 else ""

        MAP2 = {
            "->": TokenType.ARROW, "<<": TokenType.APPEND,
            "==": TokenType.EQEQ, "!=": TokenType.NEQ,
            "<=": TokenType.LTE,  ">=": TokenType.GTE,
            "+=": TokenType.PLUSEQ, "-=": TokenType.MINUSEQ,
            "*=": TokenType.STAREQ, "/=": TokenType.SLASHEQ,
        }
        MAP1 = {
            "|": TokenType.PIPE, "@": TokenType.AT, "!": TokenType.BANG,
            "~": TokenType.TILDE, "&": TokenType.AMP, ":": TokenType.COLON,
            "(": TokenType.LPAREN, ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
            "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            ",": TokenType.COMMA, ".": TokenType.DOT,
            "=": TokenType.EQ, "<": TokenType.LT, ">": TokenType.GT,
            "+": TokenType.PLUS, "-": TokenType.MINUS,
            "*": TokenType.STAR, "/": TokenType.SLASH, "%": TokenType.PERCENT,
        }

        if two in MAP2:
            self.pos += 1
            self.add(MAP2[two], two)
        elif ch in MAP1:
            self.add(MAP1[ch], ch)
        else:
            raise LexError(f"Unexpected character {ch!r} at line {self.line}")
```

- [ ] **Step 4: Run tests to confirm pass**

Run: `pytest tests/test_lexer.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/lpp/lexer.py tests/test_lexer.py
git commit -m "feat: lexer implementation"
```

---

## Task 5: Parser — Expressions

**Files:**
- Create: `src/lpp/parser.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Write expression parser tests**

```python
# tests/test_parser.py  (replace stub)
import pytest
from lpp.lexer import Lexer
from lpp.parser import Parser
from lpp.ast_nodes import *

def parse_expr(src: str) -> Expression:
    tokens = Lexer(src).tokenize()
    return Parser(tokens).parse_expression()

def test_parse_number():
    assert parse_expr("42") == NumberLiteral(42)

def test_parse_float():
    assert parse_expr("3.14") == NumberLiteral(3.14)

def test_parse_name():
    assert parse_expr("foo") == Name("foo")

def test_parse_binop_add():
    assert parse_expr("x+y") == BinOp(Name("x"), "+", Name("y"))

def test_parse_binop_compare():
    assert parse_expr("x>5") == BinOp(Name("x"), ">", NumberLiteral(5))

def test_parse_call():
    result = parse_expr("add(x,y)")
    assert isinstance(result, Call)
    assert result.func == Name("add")
    assert result.args == [Name("x"), Name("y")]

def test_parse_zero_arg_call():
    result = parse_expr("foo!")
    assert result == ZeroArgCall(Name("foo"))

def test_parse_method_zero_arg():
    result = parse_expr("msg.upper!")
    assert isinstance(result, ZeroArgCall)
    assert result.func == Attribute(Name("msg"), "upper")

def test_parse_self_attr():
    assert parse_expr("@name") == SelfAttr("name")

def test_parse_lambda_single():
    result = parse_expr("x->x*2")
    assert isinstance(result, Lambda)
    assert result.params == ["x"]
    assert result.body == BinOp(Name("x"), "*", NumberLiteral(2))

def test_parse_lambda_multi():
    result = parse_expr("x,y->x+y")
    assert isinstance(result, Lambda)
    assert result.params == ["x", "y"]

def test_parse_pipeline():
    result = parse_expr("r(10)|ma(x->x*2)|li!")
    assert isinstance(result, Pipeline)
    assert len(result.steps) == 3

def test_parse_string_no_interpolation():
    result = parse_expr('"hello"')
    assert result == StringLiteral(["hello"])

def test_parse_string_with_interpolation():
    result = parse_expr('"hello $name$!"')
    assert isinstance(result, StringLiteral)
    # parts: ["hello ", Name("name"), "!"]
    assert result.parts[0] == "hello "
    assert result.parts[1] == Name("name")
    assert result.parts[2] == "!"

def test_parse_string_escaped_dollar():
    result = parse_expr('"price: $$5"')
    assert result == StringLiteral(["price: $5"])

def test_parse_ternary():
    result = parse_expr("x if cond el y")
    assert isinstance(result, TernaryOp)
    assert result.condition == Name("cond")
    assert result.value == Name("x")
    assert result.else_value == Name("y")

def test_parse_attribute():
    result = parse_expr("obj.attr")
    assert result == Attribute(Name("obj"), "attr")

def test_parse_subscript():
    result = parse_expr("lst[0]")
    assert result == Subscript(Name("lst"), NumberLiteral(0))

def test_ast_nodes_instantiate():
    node = FunctionDef(
        name="add",
        params=[Param("x"), Param("y")],
        body=[Name("x")],
        is_method=False,
    )
    assert node.name == "add"
```

- [ ] **Step 2: Run to confirm failures**

Run: `pytest tests/test_parser.py -v`
Expected: FAILs — `ModuleNotFoundError: lpp.parser`

- [ ] **Step 3: Implement parser.py (expressions)**

```python
# src/lpp/parser.py
from .tokens import Token, TokenType
from .lexer import Lexer
from .ast_nodes import *

class ParseError(Exception):
    pass

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # --- Helpers ---

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def peek_type(self) -> TokenType:
        return self.tokens[self.pos].type

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, tt: TokenType) -> Token:
        tok = self.advance()
        if tok.type != tt:
            raise ParseError(f"Expected {tt}, got {tok.type} ({tok.value!r}) at line {tok.line}")
        return tok

    def match(self, *types: TokenType) -> bool:
        return self.peek_type() in types

    def skip_newlines(self) -> None:
        while self.match(TokenType.NEWLINE):
            self.advance()

    # --- String interpolation ---

    def _parse_string_literal(self, raw: str) -> StringLiteral:
        """Parse a raw string value containing $...$ interpolation markers."""
        parts: list[str | Expression] = []
        i = 0
        current = ""
        while i < len(raw):
            if raw[i] == "$":
                if i + 1 < len(raw) and raw[i + 1] == "$":
                    current += "$"
                    i += 2
                else:
                    end = raw.find("$", i + 1)
                    if end == -1:
                        current += raw[i:]
                        break
                    if current:
                        parts.append(current)
                        current = ""
                    expr_src = raw[i + 1:end]
                    expr_tokens = Lexer(expr_src).tokenize()
                    expr = Parser(expr_tokens).parse_expression()
                    parts.append(expr)
                    i = end + 1
            else:
                current += raw[i]
                i += 1
        if current:
            parts.append(current)
        return StringLiteral(parts)

    # --- Expression parsing ---

    def parse_expression(self) -> Expression:
        return self._parse_ternary()

    def _parse_ternary(self) -> Expression:
        value = self._parse_pipeline()
        if self.match(TokenType.IF):
            self.advance()
            condition = self._parse_pipeline()
            self.expect(TokenType.EL)
            else_value = self._parse_pipeline()
            return TernaryOp(value, condition, else_value)
        return value

    def _parse_pipeline(self) -> Expression:
        left = self._parse_lambda()
        if not self.match(TokenType.PIPE):
            return left
        steps = [left]
        while self.match(TokenType.PIPE):
            self.advance()
            steps.append(self._parse_lambda())
        return Pipeline(steps)

    def _parse_lambda(self) -> Expression:
        # Lambda: ident -> expr  OR  ident,ident -> expr
        # We need lookahead to distinguish `x->...` from just `x`
        save = self.pos
        try:
            params = []
            if self.match(TokenType.IDENT):
                params.append(self.advance().value)
                while self.match(TokenType.COMMA):
                    self.advance()
                    params.append(self.expect(TokenType.IDENT).value)
                if self.match(TokenType.ARROW):
                    self.advance()
                    body = self._parse_or()
                    return Lambda(params, body)
            self.pos = save
        except ParseError:
            self.pos = save
        return self._parse_or()

    def _parse_or(self) -> Expression:
        left = self._parse_and()
        while self.peek_type() == TokenType.IDENT and self.peek().value == "or":
            self.advance()
            right = self._parse_and()
            left = BinOp(left, "or", right)
        return left

    def _parse_and(self) -> Expression:
        left = self._parse_not()
        while self.peek_type() == TokenType.IDENT and self.peek().value == "and":
            self.advance()
            right = self._parse_not()
            left = BinOp(left, "and", right)
        return left

    def _parse_not(self) -> Expression:
        if self.match(TokenType.TILDE):
            self.advance()
            return UnaryOp("not", self._parse_not())
        return self._parse_comparison()

    def _parse_comparison(self) -> Expression:
        left = self._parse_additive()
        OPS = {
            TokenType.EQEQ: "==", TokenType.NEQ: "!=",
            TokenType.LT: "<", TokenType.GT: ">",
            TokenType.LTE: "<=", TokenType.GTE: ">=",
        }
        if self.peek_type() in OPS:
            op = OPS[self.advance().type]
            right = self._parse_additive()
            return BinOp(left, op, right)
        if self.peek_type() == TokenType.IN:
            self.advance()
            right = self._parse_additive()
            return BinOp(left, "in", right)
        return left

    def _parse_additive(self) -> Expression:
        left = self._parse_multiplicative()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.advance().value
            right = self._parse_multiplicative()
            left = BinOp(left, op, right)
        return left

    def _parse_multiplicative(self) -> Expression:
        left = self._parse_unary()
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance().value
            right = self._parse_unary()
            left = BinOp(left, op, right)
        return left

    def _parse_unary(self) -> Expression:
        if self.match(TokenType.MINUS):
            self.advance()
            return UnaryOp("-", self._parse_postfix())
        return self._parse_postfix()

    def _parse_postfix(self) -> Expression:
        expr = self._parse_primary()
        while True:
            if self.match(TokenType.BANG):
                self.advance()
                expr = ZeroArgCall(expr)
            elif self.match(TokenType.DOT):
                self.advance()
                attr = self.expect(TokenType.IDENT).value
                expr = Attribute(expr, attr)
            elif self.match(TokenType.LPAREN):
                expr = self._parse_call(expr)
            elif self.match(TokenType.LBRACKET):
                self.advance()
                key = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                expr = Subscript(expr, key)
            else:
                break
        return expr

    def _parse_call(self, func: Expression) -> Call:
        self.expect(TokenType.LPAREN)
        args = []
        kwargs = {}
        while not self.match(TokenType.RPAREN, TokenType.EOF):
            # keyword arg: ident=expr
            if self.peek_type() == TokenType.IDENT and self.tokens[self.pos + 1].type == TokenType.EQ:
                key = self.advance().value
                self.advance()  # skip =
                kwargs[key] = self.parse_expression()
            else:
                if self.match(TokenType.STAR):
                    self.advance()
                    args.append(Spread(self.parse_expression()))
                else:
                    args.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.advance()
        self.expect(TokenType.RPAREN)
        return Call(func, args, kwargs)

    def _parse_primary(self) -> Expression:
        tok = self.peek()

        if tok.type == TokenType.NUMBER:
            self.advance()
            val = tok.value
            return NumberLiteral(float(val) if "." in val else int(val))

        if tok.type == TokenType.STRING:
            self.advance()
            return self._parse_string_literal(tok.value)

        if tok.type == TokenType.AT:
            self.advance()
            attr = self.expect(TokenType.IDENT).value
            return SelfAttr(attr)

        if tok.type == TokenType.IDENT:
            self.advance()
            return Name(tok.value)

        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        if tok.type == TokenType.LBRACKET:
            self.advance()
            elements = []
            while not self.match(TokenType.RBRACKET, TokenType.EOF):
                elements.append(self.parse_expression())
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RBRACKET)
            return ListLiteral(elements)

        if tok.type == TokenType.LBRACE:
            self.advance()
            pairs = []
            while not self.match(TokenType.RBRACE, TokenType.EOF):
                key = self.parse_expression()
                self.expect(TokenType.COLON)
                val = self.parse_expression()
                pairs.append((key, val))
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RBRACE)
            return DictLiteral(pairs)

        raise ParseError(f"Unexpected token {tok.type} ({tok.value!r}) at line {tok.line}")

    # --- Statement parsing (stub — implemented in Task 6) ---

    def parse(self) -> Program:
        raise NotImplementedError("Implemented in Task 6")
```

- [ ] **Step 4: Run expression tests to confirm pass**

Run: `pytest tests/test_parser.py -v -k "not test_ast_nodes_instantiate" --ignore-glob="*integration*"`
Expected: expression tests PASS, `test_ast_nodes_instantiate` also PASS

- [ ] **Step 5: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat: expression parser"
```

---

## Task 6: Parser — Statements

**Files:**
- Modify: `src/lpp/parser.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Add statement parser tests**

```python
# Append to tests/test_parser.py

from lpp.parser import Parser
from lpp.lexer import Lexer

def parse_prog(src: str) -> Program:
    tokens = Lexer(src).tokenize()
    return Parser(tokens).parse()

def first(src: str):
    return parse_prog(src).body[0]

def test_parse_assignment():
    node = first("x=42")
    assert isinstance(node, Assignment)
    assert node.target == "x"
    assert node.value == NumberLiteral(42)

def test_parse_aug_assignment():
    node = first("x+=1")
    assert isinstance(node, AugAssignment)
    assert node.op == "+="

def test_parse_function_def():
    node = first("fn add x y\n  x+y\n")
    assert isinstance(node, FunctionDef)
    assert node.name == "add"
    assert node.params == [Param("x"), Param("y")]
    assert not node.is_method

def test_parse_function_default_param():
    node = first("fn greet name loud=0\n  name\n")
    assert isinstance(node, FunctionDef)
    assert node.params[1] == Param("loud", NumberLiteral(0))

def test_parse_method():
    src = "cls Dog\n  fn @bark\n    p!\n"
    node = first(src)
    assert isinstance(node, ClassDef)
    method = node.body[0]
    assert method.is_method
    assert method.name == "bark"

def test_parse_if_else():
    src = "if x>5\n  p(\"big\")\nel\n  p(\"small\")\n"
    node = first(src)
    assert isinstance(node, IfStatement)
    assert len(node.elifs) == 1
    cond, _ = node.elifs[0]
    assert cond is None  # bare el

def test_parse_elif():
    src = "if x>5\n  a\nel x==5\n  b\nel\n  c\n"
    node = first(src)
    assert len(node.elifs) == 2
    assert node.elifs[0][0] == BinOp(Name("x"), "==", NumberLiteral(5))
    assert node.elifs[1][0] is None

def test_parse_for():
    src = "for i in r(10)\n  p(i)\n"
    node = first(src)
    assert isinstance(node, ForStatement)
    assert node.targets == ["i"]

def test_parse_for_tuple_unpack():
    src = "for k,v in d.items!\n  p(k)\n"
    node = first(src)
    assert node.targets == ["k", "v"]

def test_parse_do():
    src = "do x>0\n  x-=1\n"
    node = first(src)
    assert isinstance(node, DoStatement)

def test_parse_try_err():
    src = "try\n  i(val)\nerr ValueError e\n  p(e)\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert node.handlers[0].exc_type == "ValueError"
    assert node.handlers[0].name == "e"

def test_parse_ret():
    src = "fn f\n  ret 42\n"
    node = first(src)
    assert isinstance(node.body[0], RetStatement)
    assert node.body[0].value == NumberLiteral(42)

def test_parse_use_simple():
    node = first("use os,json\n")
    assert isinstance(node, UseStatement)
    assert node.imports[0].module == "os"
    assert node.imports[1].module == "json"

def test_parse_use_alias():
    node = first("use np=numpy\n")
    assert isinstance(node, UseStatement)
    assert node.imports[0].module == "numpy"
    assert node.imports[0].alias == "np"

def test_parse_use_from():
    node = first("use pathlib:Path\n")
    assert isinstance(node, UseStatement)
    assert node.imports[0].module == "pathlib"
    assert node.imports[0].item == "Path"

def test_parse_alias():
    node = first("alias sq=math.sqrt\n")
    assert isinstance(node, AliasStatement)
    assert node.name == "sq"

def test_parse_append():
    node = first("items<<x\n")
    assert isinstance(node, AppendStatement)
    assert node.target == Name("items")
    assert node.value == Name("x")
```

- [ ] **Step 2: Run to confirm failures**

Run: `pytest tests/test_parser.py -v -k "parse_assignment or parse_function or parse_if or parse_for or parse_do or parse_try or parse_ret or parse_use or parse_alias or parse_append or parse_method"`
Expected: FAILs — `NotImplementedError: Implemented in Task 6`

- [ ] **Step 3: Implement statement parsing in parser.py**

Replace the `parse` stub in `src/lpp/parser.py` with:

```python
    def parse(self) -> Program:
        self.skip_newlines()
        body = []
        while not self.match(TokenType.EOF):
            body.append(self._parse_statement())
            self.skip_newlines()
        return Program(body)

    def _parse_block(self) -> list[Statement]:
        self.expect(TokenType.INDENT)
        stmts = []
        self.skip_newlines()
        while not self.match(TokenType.DEDENT, TokenType.EOF):
            stmts.append(self._parse_statement())
            self.skip_newlines()
        if self.match(TokenType.DEDENT):
            self.advance()
        return stmts

    def _parse_statement(self) -> Statement:
        tt = self.peek_type()

        if tt == TokenType.FN:
            return self._parse_function()
        if tt == TokenType.CLS:
            return self._parse_class()
        if tt == TokenType.IF:
            return self._parse_if()
        if tt == TokenType.FOR:
            return self._parse_for()
        if tt == TokenType.DO:
            return self._parse_do()
        if tt == TokenType.TRY:
            return self._parse_try()
        if tt == TokenType.RET:
            return self._parse_ret()
        if tt == TokenType.USE:
            return self._parse_use()
        if tt == TokenType.ALIAS:
            return self._parse_alias()

        # Could be assignment, aug-assignment, append, or expression statement
        return self._parse_expr_or_assign()

    def _parse_function(self) -> FunctionDef:
        self.expect(TokenType.FN)
        is_method = self.match(TokenType.AT)
        if is_method:
            self.advance()
        name = self.expect(TokenType.IDENT).value
        params = self._parse_params()
        self.skip_newlines()
        body = self._parse_block()
        return FunctionDef(name, params, body, is_method)

    def _parse_params(self) -> list[Param]:
        params = []
        while self.match(TokenType.IDENT):
            pname = self.advance().value
            default = None
            if self.match(TokenType.EQ):
                self.advance()
                default = self.parse_expression()
            params.append(Param(pname, default))
        return params

    def _parse_class(self) -> ClassDef:
        self.expect(TokenType.CLS)
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
            methods.append(self._parse_function())
            self.skip_newlines()
        if self.match(TokenType.DEDENT):
            self.advance()
        return ClassDef(name, base, methods)

    def _parse_if(self) -> IfStatement:
        self.expect(TokenType.IF)
        condition = self.parse_expression()
        self.skip_newlines()
        body = self._parse_block()
        elifs = []
        while self.match(TokenType.EL):
            self.advance()
            if self.match(TokenType.NEWLINE, TokenType.INDENT):
                # bare el = else
                self.skip_newlines()
                elifs.append((None, self._parse_block()))
                break
            else:
                # el with condition = elif
                cond = self.parse_expression()
                self.skip_newlines()
                elifs.append((cond, self._parse_block()))
        return IfStatement(condition, body, elifs)

    def _parse_for(self) -> ForStatement:
        self.expect(TokenType.FOR)
        targets = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.COMMA):
            self.advance()
            targets.append(self.expect(TokenType.IDENT).value)
        self.expect(TokenType.IN)
        iterable = self.parse_expression()
        self.skip_newlines()
        body = self._parse_block()
        return ForStatement(targets, iterable, body)

    def _parse_do(self) -> DoStatement:
        self.expect(TokenType.DO)
        condition = self.parse_expression()
        self.skip_newlines()
        body = self._parse_block()
        return DoStatement(condition, body)

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
        return TryStatement(body, handlers)

    def _parse_ret(self) -> RetStatement:
        self.expect(TokenType.RET)
        value = None
        if not self.match(TokenType.NEWLINE, TokenType.EOF):
            value = self.parse_expression()
        if self.match(TokenType.NEWLINE):
            self.advance()
        return RetStatement(value)

    def _parse_use(self) -> UseStatement:
        self.expect(TokenType.USE)
        imports = []
        while True:
            # Could be: ident, alias=module, module:item, module:item=alias
            alias = None
            item = None
            # Peek ahead for alias= pattern
            if (self.peek_type() == TokenType.IDENT and
                    self.tokens[self.pos + 1].type == TokenType.EQ):
                alias = self.advance().value
                self.advance()  # skip =
            module = self.expect(TokenType.IDENT).value
            if self.match(TokenType.COLON):
                self.advance()
                item = self.expect(TokenType.IDENT).value
                if self.match(TokenType.EQ):
                    self.advance()
                    alias = self.expect(TokenType.IDENT).value
            imports.append(UseImport(module, item, alias))
            if not self.match(TokenType.COMMA):
                break
            self.advance()
        if self.match(TokenType.NEWLINE):
            self.advance()
        return UseStatement(imports)

    def _parse_alias(self) -> AliasStatement:
        self.expect(TokenType.ALIAS)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.EQ)
        target = self.parse_expression()
        if self.match(TokenType.NEWLINE):
            self.advance()
        return AliasStatement(name, target)

    def _parse_expr_or_assign(self) -> Statement:
        # Lookahead: ident = expr, ident += expr, expr << expr
        save = self.pos

        # Try ident = / ident OP=
        if self.peek_type() == TokenType.IDENT:
            name = self.advance().value
            AUG = {
                TokenType.PLUSEQ: "+=", TokenType.MINUSEQ: "-=",
                TokenType.STAREQ: "*=", TokenType.SLASHEQ: "/=",
            }
            if self.peek_type() in AUG:
                op = AUG[self.advance().type]
                value = self.parse_expression()
                if self.match(TokenType.NEWLINE):
                    self.advance()
                return AugAssignment(name, op, value)
            if self.peek_type() == TokenType.EQ:
                self.advance()
                value = self.parse_expression()
                if self.match(TokenType.NEWLINE):
                    self.advance()
                return Assignment(name, value)
            self.pos = save

        # Try expr << expr (append)
        expr = self.parse_expression()
        if self.match(TokenType.APPEND):
            self.advance()
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE):
                self.advance()
            return AppendStatement(expr, value)

        if self.match(TokenType.NEWLINE):
            self.advance()
        return ExprStatement(expr)
```

- [ ] **Step 4: Run all parser tests**

Run: `pytest tests/test_parser.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py
git commit -m "feat: statement parser"
```

---

## Task 7: Prelude

**Files:**
- Create: `src/lpp/prelude.py`
- Create: `tests/test_prelude.py`

- [ ] **Step 1: Write prelude tests**

```python
# tests/test_prelude.py
from lpp.prelude import PRELUDE, inject_prelude

def test_prelude_contains_single_char():
    for alias in ["p", "l", "r", "s", "i", "f", "b", "t"]:
        assert alias in PRELUDE, f"Missing single-char alias: {alias}"

def test_prelude_contains_two_char():
    for alias in ["li", "di", "se", "tu", "en", "zi", "ma", "fi",
                  "so", "rv", "su", "mn", "mx", "ab", "ro", "an",
                  "al", "nx", "ip", "op", "rp", "ga", "sa", "ha",
                  "od", "ch", "pw", "hx", "is", "sc"]:
        assert alias in PRELUDE, f"Missing two-char alias: {alias}"

def test_no_alias_conflicts():
    assert len(PRELUDE) == len(set(PRELUDE.keys())), "Duplicate alias keys"
    assert len(PRELUDE) == len(set(PRELUDE.values())), "Duplicate alias targets"

def test_inject_prelude_prepends():
    python_src = "x = 1\n"
    result = inject_prelude(python_src)
    assert result.startswith("# L++ prelude")
    assert "print" in result
    assert "x = 1" in result
```

- [ ] **Step 2: Run to confirm failures**

Run: `pytest tests/test_prelude.py -v`
Expected: FAILs — `ModuleNotFoundError: lpp.prelude`

- [ ] **Step 3: Implement prelude.py**

```python
# src/lpp/prelude.py

PRELUDE: dict[str, str] = {
    # Single-char
    "p":  "print",
    "l":  "len",
    "r":  "range",
    "s":  "str",
    "i":  "int",
    "f":  "float",
    "b":  "bool",
    "t":  "type",
    # Two-char
    "li": "list",
    "di": "dict",
    "se": "set",
    "tu": "tuple",
    "en": "enumerate",
    "zi": "zip",
    "ma": "map",
    "fi": "filter",
    "so": "sorted",
    "rv": "reversed",
    "su": "sum",
    "mn": "min",
    "mx": "max",
    "ab": "abs",
    "ro": "round",
    "an": "any",
    "al": "all",
    "nx": "next",
    "ip": "input",
    "op": "open",
    "rp": "repr",
    "ga": "getattr",
    "sa": "setattr",
    "ha": "hasattr",
    "od": "ord",
    "ch": "chr",
    "pw": "pow",
    "hx": "hex",
    "is": "isinstance",
    "sc": "issubclass",
}

def inject_prelude(python_src: str) -> str:
    lines = ["# L++ prelude"]
    for alias, target in PRELUDE.items():
        lines.append(f"{alias} = {target}")
    lines.append("")
    return "\n".join(lines) + "\n" + python_src
```

- [ ] **Step 4: Run tests to confirm pass**

Run: `pytest tests/test_prelude.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/lpp/prelude.py tests/test_prelude.py
git commit -m "feat: standard prelude"
```

---

## Task 8: Transpiler — Core

**Files:**
- Create: `src/lpp/transpiler.py`
- Create: `tests/test_transpiler.py`

- [ ] **Step 1: Write transpiler tests**

```python
# tests/test_transpiler.py
import pytest
from lpp import compile_lpp

def py(src: str) -> str:
    """Compile L++ and strip prelude for test clarity."""
    full = compile_lpp(src)
    # Strip prelude lines (up to first blank line after prelude)
    lines = full.split("\n")
    start = next(i for i, l in enumerate(lines) if l == "") + 1
    return "\n".join(lines[start:]).strip()

# Expressions
def test_binop():
    assert py("x+y\n") == "x + y"

def test_number():
    assert py("42\n") == "42"

def test_string_plain():
    assert py('"hello"\n') == '"hello"'

def test_string_interpolated():
    # Transpiler emits f-string when interpolation markers present
    result = py('"hello $name$!"\n')
    assert result == 'f"hello {name}!"'

def test_string_escaped_dollar():
    result = py('"price: $$5"\n')
    assert result == '"price: $5"'

def test_zero_arg_call():
    assert py("foo!\n") == "foo()"

def test_method_zero_arg():
    assert py("msg.upper!\n") == "msg.upper()"

def test_pipeline():
    # Transpiler emits aliases (li, r) — prelude resolves them at runtime
    result = py("r(10)|li!\n")
    assert result == "li(r(10))"

def test_pipeline_three():
    # ma(lambda, source) wrapping; aliases preserved
    result = py("r(10)|ma(x->x*2)|li!\n")
    assert result == "li(ma(lambda x: x * 2, r(10)))"

def test_lambda():
    assert py("x->x*2\n") == "lambda x: x * 2"

def test_self_attr():
    assert py("@name\n") == "self.name"

def test_ternary():
    assert py("x if cond el y\n") == "x if cond else y"

# Statements
def test_assignment():
    assert py("x=42\n") == "x = 42"

def test_aug_assignment():
    assert py("x+=1\n") == "x += 1"

def test_append():
    assert py("items<<x\n") == "items.append(x)"

def test_ret():
    assert py("fn f\n  ret 42\n") == "def f():\n    return 42"

def test_function_implicit_return():
    result = py("fn add x y\n  x+y\n")
    assert result == "def add(x, y):\n    return x + y"

def test_function_default_param():
    result = py("fn greet name loud=0\n  name\n")
    assert "def greet(name, loud=0):" in result

def test_method():
    src = "cls Dog\n  fn @bark\n    p!\n"
    result = py(src)
    assert "def bark(self):" in result
    assert "p()" in result  # p is the prelude alias — transpiler emits p(), not print()

def test_class_inheritance():
    # Use a real L++ body — 'pass' is not an L++ keyword
    result = py("cls GoldenRetriever:Dog\n  fn @init name\n    @name=name\n")
    assert "class GoldenRetriever(Dog):" in result

def test_if_else():
    src = 'if x>5\n  p("big")\nel\n  p("small")\n'
    result = py(src)
    assert "if x > 5:" in result
    assert "else:" in result

def test_elif():
    src = 'if x>5\n  p("big")\nel x==5\n  p("mid")\nel\n  p("small")\n'
    result = py(src)
    assert "elif x == 5:" in result

def test_for():
    # r is the prelude alias for range — transpiler emits r, not range
    result = py("for i in r(10)\n  p(i)\n")
    assert "for i in r(10):" in result
    assert "p(i)" in result

def test_for_tuple_unpack():
    result = py("for k,v in d.items!\n  p(k)\n")
    assert "for k, v in d.items():" in result

def test_do():
    result = py("do x>0\n  x-=1\n")
    assert "while x > 0:" in result

def test_try_err():
    src = "try\n  i(val)\nerr ValueError e\n  p(e)\n"
    result = py(src)
    assert "try:" in result
    assert "except ValueError as e:" in result

def test_use_simple():
    result = py("use os\n")
    assert "import os" in result

def test_use_alias():
    result = py("use np=numpy\n")
    assert "import numpy as np" in result

def test_use_from():
    result = py("use pathlib:Path\n")
    assert "from pathlib import Path" in result

def test_use_from_alias():
    result = py("use pathlib:Path=P\n")
    assert "from pathlib import Path as P" in result

def test_alias_statement():
    result = py("alias sq=math.sqrt\n")
    assert "sq = math.sqrt" in result
```

- [ ] **Step 2: Run to confirm failures**

Run: `pytest tests/test_transpiler.py -v`
Expected: FAILs — `NotImplementedError` or `ModuleNotFoundError: lpp.transpiler`

- [ ] **Step 3: Implement transpiler.py**

```python
# src/lpp/transpiler.py
from .ast_nodes import *
from .prelude import inject_prelude

INDENT = "    "

class Transpiler:
    def transpile(self, program: Program) -> str:
        lines = [self._stmt(node, 0) for node in program.body]
        python_src = "\n".join(lines) + "\n"
        return inject_prelude(python_src)

    # --- Statements ---

    def _stmt(self, node: Statement, depth: int) -> str:
        pad = INDENT * depth
        match node:
            case FunctionDef():
                return self._fn(node, depth)
            case ClassDef():
                return self._cls(node, depth)
            case Assignment(target, value):
                return f"{pad}{target} = {self._expr(value)}"
            case AugAssignment(target, op, value):
                return f"{pad}{target} {op} {self._expr(value)}"
            case AppendStatement(target, value):
                return f"{pad}{self._expr(target)}.append({self._expr(value)})"
            case IfStatement():
                return self._if(node, depth)
            case ForStatement():
                return self._for(node, depth)
            case DoStatement(condition, body):
                lines = [f"{pad}while {self._expr(condition)}:"]
                lines += [self._stmt(s, depth + 1) for s in body]
                return "\n".join(lines)
            case TryStatement():
                return self._try(node, depth)
            case RetStatement(value):
                val = f" {self._expr(value)}" if value is not None else ""
                return f"{pad}return{val}"
            case UseStatement(imports):
                return "\n".join(self._use(imp) for imp in imports)
            case AliasStatement(name, target):
                return f"{pad}{name} = {self._expr(target)}"
            case ExprStatement(expr):
                return f"{pad}{self._expr(expr)}"
            case _:
                raise NotImplementedError(f"Unknown statement: {type(node)}")

    def _fn(self, node: FunctionDef, depth: int) -> str:
        pad = INDENT * depth
        params = []
        if node.is_method:
            params.append("self")
        for p in node.params:
            if p.default is not None:
                params.append(f"{p.name}={self._expr(p.default)}")
            else:
                params.append(p.name)
        param_str = ", ".join(params)
        lines = [f"{pad}def {node.name}({param_str}):"]
        if not node.body:
            lines.append(f"{INDENT * (depth + 1)}pass")
        else:
            *body, last = node.body
            for s in body:
                lines.append(self._stmt(s, depth + 1))
            # Last statement: implicit return if it's an expression
            if isinstance(last, ExprStatement):
                lines.append(f"{INDENT * (depth + 1)}return {self._expr(last.expr)}")
            else:
                lines.append(self._stmt(last, depth + 1))
        return "\n".join(lines)

    def _cls(self, node: ClassDef, depth: int) -> str:
        pad = INDENT * depth
        base = f"({node.base})" if node.base else ""
        lines = [f"{pad}class {node.name}{base}:"]
        for method in node.body:
            lines.append(self._fn(method, depth + 1))
        return "\n".join(lines)

    def _if(self, node: IfStatement, depth: int) -> str:
        pad = INDENT * depth
        lines = [f"{pad}if {self._expr(node.condition)}:"]
        lines += [self._stmt(s, depth + 1) for s in node.body]
        for cond, body in node.elifs:
            if cond is None:
                lines.append(f"{pad}else:")
            else:
                lines.append(f"{pad}elif {self._expr(cond)}:")
            lines += [self._stmt(s, depth + 1) for s in body]
        return "\n".join(lines)

    def _for(self, node: ForStatement, depth: int) -> str:
        pad = INDENT * depth
        targets = ", ".join(node.targets)
        lines = [f"{pad}for {targets} in {self._expr(node.iterable)}:"]
        lines += [self._stmt(s, depth + 1) for s in node.body]
        return "\n".join(lines)

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
        return "\n".join(lines)

    def _use(self, imp: UseImport) -> str:
        if imp.item:
            alias_part = f" as {imp.alias}" if imp.alias else ""
            return f"from {imp.module} import {imp.item}{alias_part}"
        elif imp.alias:
            return f"import {imp.module} as {imp.alias}"
        else:
            return f"import {imp.module}"

    # --- Expressions ---

    def _expr(self, node: Expression) -> str:
        match node:
            case NumberLiteral(value):
                return str(value) if not isinstance(value, float) or value != int(value) else str(int(value))
            case StringLiteral(parts):
                return self._string(parts)
            case Name(id):
                return id
            case SelfAttr(attr):
                return f"self.{attr}"
            case Attribute(obj, attr):
                return f"{self._expr(obj)}.{attr}"
            case Subscript(obj, key):
                return f"{self._expr(obj)}[{self._expr(key)}]"
            case BinOp(left, op, right):
                return f"{self._expr(left)} {op} {self._expr(right)}"
            case UnaryOp(op, operand):
                py_op = "not " if op == "not" else op
                return f"{py_op}{self._expr(operand)}"
            case Call(func, args, kwargs):
                return self._call(func, args, kwargs)
            case ZeroArgCall(func):
                return f"{self._expr(func)}()"
            case Pipeline(steps):
                return self._pipeline(steps)
            case Lambda(params, body):
                return f"lambda {', '.join(params)}: {self._expr(body)}"
            case TernaryOp(value, condition, else_value):
                return f"{self._expr(value)} if {self._expr(condition)} else {self._expr(else_value)}"
            case ListLiteral(elements):
                return f"[{', '.join(self._expr(e) for e in elements)}]"
            case DictLiteral(pairs):
                items = ", ".join(f"{self._expr(k)}: {self._expr(v)}" for k, v in pairs)
                return "{" + items + "}"
            case Spread(value):
                return f"*{self._expr(value)}"
            case _:
                raise NotImplementedError(f"Unknown expression: {type(node)}")

    def _string(self, parts: list) -> str:
        if all(isinstance(p, str) for p in parts):
            inner = "".join(parts)
            return f'"{inner}"'
        inner = ""
        for part in parts:
            if isinstance(part, str):
                inner += part.replace("{", "{{").replace("}", "}}")
            else:
                inner += "{" + self._expr(part) + "}"
        return f'f"{inner}"'

    def _call(self, func: Expression, args: list, kwargs: dict) -> str:
        all_args = [self._expr(a) for a in args]
        all_args += [f"{k}={self._expr(v)}" for k, v in kwargs.items()]
        return f"{self._expr(func)}({', '.join(all_args)})"

    def _pipeline(self, steps: list[Expression]) -> str:
        # r(10)|ma(x->x*2)|li!  →  list(map(lambda x: x*2, range(10)))
        # Build right-to-left: each step wraps the previous result
        # Step 0 is the source; each subsequent step is a callable applied to it
        result = self._expr(steps[0])
        for step in steps[1:]:
            fn = self._expr(step)
            # If step is a ZeroArgCall, strip the ()
            if isinstance(step, ZeroArgCall):
                fn = self._expr(step.func)
                result = f"{fn}({result})"
            elif isinstance(step, Call):
                # ma(x->x*2) → map(lambda x: x*2, <prev>)
                inner_args = ", ".join(self._expr(a) for a in step.args)
                result = f"{self._expr(step.func)}({inner_args}, {result})"
            else:
                result = f"{fn}({result})"
        return result
```

- [ ] **Step 4: Run transpiler tests**

Run: `pytest tests/test_transpiler.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/lpp/transpiler.py tests/test_transpiler.py
git commit -m "feat: transpiler core"
```

---

## Task 9: CLI

**Files:**
- Create: `src/lpp/cli.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration + CLI tests**

```python
# tests/test_integration.py
import subprocess, sys, textwrap, tempfile, os
from lpp import compile_lpp

def run_lpp(src: str) -> str:
    """Compile L++ and execute it, return stdout."""
    python_src = compile_lpp(src)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(python_src)
        path = f.name
    try:
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        return result.stdout.strip()
    finally:
        os.unlink(path)

def test_hello_world():
    assert run_lpp('p("hello world")\n') == "hello world"

def test_function_call():
    src = textwrap.dedent("""\
        fn add x y
          x+y
        p(add(3,4))
    """)
    assert run_lpp(src) == "7"

def test_string_interpolation():
    src = 'name="world"\np("hello $name$!")\n'
    assert run_lpp(src) == "hello world!"

def test_for_loop():
    src = textwrap.dedent("""\
        r=[]\
        for i in r(3)
          r<<i
        p(r)
    """)
    # Note: r is shadowed by the list — rename to avoid prelude conflict
    src = textwrap.dedent("""\
        acc=[]
        for i in r(3)
          acc<<i
        p(acc)
    """)
    assert run_lpp(src) == "[0, 1, 2]"

def test_pipeline():
    src = "p(r(5)|ma(x->x*2)|li!)\n"
    assert run_lpp(src) == "[0, 2, 4, 6, 8]"

def test_class():
    src = textwrap.dedent("""\
        cls Dog
          fn @init name
            @name=name
          fn @bark
            p("Woof! I'm $@name$")
        d=Dog("Rex")
        d.bark!
    """)
    assert run_lpp(src) == "Woof! I'm Rex"
```

- [ ] **Step 2: Run to confirm integration failures**

Run: `pytest tests/test_integration.py -v`
Expected: some FAILs (CLI not yet wired up, but `compile_lpp` may work)

- [ ] **Step 3: Implement cli.py**

```python
# src/lpp/cli.py
import sys
import argparse
from . import compile_lpp

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lpp",
        description="L++ transpiler — compile .lpp files to Python",
    )
    parser.add_argument("file", help=".lpp source file")
    parser.add_argument("-o", "--output", help="write Python output to file instead of stdout")
    parser.add_argument("--run", action="store_true", help="execute transpiled Python immediately")
    args = parser.parse_args()

    with open(args.file) as f:
        source = f.read()

    python_src = compile_lpp(source)

    if args.run:
        exec(compile(python_src, args.file, "exec"), {"__name__": "__main__"})
    elif args.output:
        with open(args.output, "w") as f:
            f.write(python_src)
        print(f"Written to {args.output}")
    else:
        print(python_src)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: all PASS

- [ ] **Step 5: Test CLI manually**

```bash
echo 'p("hello from lpp!")' > hello.lpp
lpp hello.lpp --run
```
Expected output: `hello from lpp!`

- [ ] **Step 6: Commit**

```bash
git add src/lpp/cli.py tests/test_integration.py
git commit -m "feat: CLI and integration tests"
```

---

## Task 10: Full Test Suite Pass

**Files:** None new — verify everything passes together.

- [ ] **Step 1: Run full suite**

Run: `pytest -v`
Expected: all tests PASS with no warnings

- [ ] **Step 2: Test a non-trivial program end-to-end**

Create `examples/fizzbuzz.lpp`:

```
for i in r(1,101)
  if i%15==0
    p("FizzBuzz")
  el i%3==0
    p("Fizz")
  el i%5==0
    p("Buzz")
  el
    p(i)
```

Run: `lpp examples/fizzbuzz.lpp --run | head -20`
Expected: `1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz ...`

- [ ] **Step 3: Final commit**

```bash
git add examples/
git commit -m "feat: fizzbuzz example, all tests passing"
```

---

## Open Items (from spec)

These are deferred to future plan iterations:

- Tokenizer validation pass — run every keyword and prelude alias through cl100k to confirm single-token status
- Decorator syntax — `@` is taken by self
- Generator / yield syntax
- Async / await syntax
- Multi-target transpilation (JS, Rust)
- Formal grammar (BNF/PEG)
- Bitwise OR alternative (since `|` is pipeline)
- `is` alias vs Python identity operator — consider `ic`
