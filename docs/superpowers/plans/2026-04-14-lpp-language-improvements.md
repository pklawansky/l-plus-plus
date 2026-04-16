# L++ Language Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement five language improvements: function composition operator (`&`), dotted module names in `use`, dead token cleanup, structured error messages with source context, and a cl100k tokenizer validation script.

**Architecture:** All changes are additive or corrective — no existing behaviour changes except dead token removal (which frees `as` as an identifier and removes `::` from the lexer). Each task is independent and can be reviewed in isolation.

**Tech Stack:** Python 3.11+, pytest, tiktoken (Task 5 only).

---

## File Structure

```
l-plus-plus/
  src/lpp/
    tokens.py       # Task 3: remove AS from KEYWORDS, remove COLONCOLON from TokenType
    lexer.py        # Task 3: remove :: from MAP2; Task 4: add col tracking + structured LexError
    ast_nodes.py    # Task 1: add Compose node
    parser.py       # Task 1: add _parse_compose; Task 2: dotted module names; Task 4: structured ParseError
    transpiler.py   # Task 1: emit Compose
    cli.py          # Task 4: format errors with source context
  tools/
    validate_tokens.py   # Task 5: cl100k validation script
  tests/
    test_lexer.py        # Tasks 3, 4
    test_parser.py       # Tasks 1, 2, 4
    test_transpiler.py   # Tasks 1, 2
    test_integration.py  # Task 1
```

---

## Codebase Context

Key files the implementer must understand:

- `src/lpp/tokens.py` — `TokenType` enum (64 members), `KEYWORDS` dict, `Token` dataclass with `type`, `value`, `line`.
- `src/lpp/lexer.py` — `Lexer` class. `_scan_operator` uses `MAP2` (2-char) and `MAP1` (1-char) dicts. `TokenType.AMP` (`&`) is already lexed by MAP1.
- `src/lpp/ast_nodes.py` — All AST nodes as dataclasses. `Expression` is a `Union` type alias at the top listing every expression node.
- `src/lpp/parser.py` — Recursive descent. Expression precedence chain: `_parse_ternary → _parse_pipeline → _parse_lambda → _parse_or → _parse_and → _parse_not → _parse_comparison → _parse_additive → _parse_multiplicative → _parse_unary → _parse_postfix → _parse_primary`. `_parse_lambda` calls `self._parse_or()` as its fallback.
- `src/lpp/transpiler.py` — `Transpiler._expr` dispatches on node type via `match`. `_pipeline` handles `Pipeline` nodes specially.
- `src/lpp/prelude.py` — `PRELUDE: dict[str, str]` with 38 aliases.

---

## Task 1: Function Composition (`f&g`)

**Spec:** `&` means "function composition". `f&g` produces a callable where `(f&g)(x)` = `f(g(x))`. Left-associative: `f&g&h` = `(f&g)&h`.

**Files:**
- Modify: `src/lpp/ast_nodes.py`
- Modify: `src/lpp/parser.py`
- Modify: `src/lpp/transpiler.py`
- Test: `tests/test_parser.py`
- Test: `tests/test_transpiler.py`
- Test: `tests/test_integration.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_parser.py`:

```python
def test_parse_compose():
    from lpp.ast_nodes import Compose, Name
    node = parse_expr("f&g")
    assert node == Compose(Name("f"), Name("g"))

def test_parse_compose_chain():
    from lpp.ast_nodes import Compose, Name
    node = parse_expr("f&g&h")
    assert node == Compose(Compose(Name("f"), Name("g")), Name("h"))
```

Add to `tests/test_transpiler.py`:

```python
def test_compose():
    result = py("h=f&g\n")
    assert result == "h = (lambda *a, **kw: f(g(*a, **kw)))"

def test_compose_chain():
    result = py("h=f&g&k\n")
    assert result == "h = (lambda *a, **kw: (lambda *a, **kw: f(g(*a, **kw)))(k(*a, **kw)))"
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/test_parser.py::test_parse_compose tests/test_transpiler.py::test_compose -v
```

Expected: FAIL — `ImportError: cannot import name 'Compose'`

- [ ] **Step 3: Add `Compose` to `ast_nodes.py`**

In `src/lpp/ast_nodes.py`, add `"Compose"` to the `Expression` union at the top of the file:

```python
Expression = Union[
    "BinOp", "UnaryOp", "Call", "ZeroArgCall", "Pipeline",
    "Lambda", "Compose", "Name", "SelfAttr", "Attribute", "Subscript",
    "StringLiteral", "NumberLiteral", "ListLiteral", "DictLiteral",
    "TernaryOp", "Spread",
]
```

Add the `Compose` dataclass after `Lambda`:

```python
@dataclass
class Compose:
    left: Expression
    right: Expression
```

- [ ] **Step 4: Add `_parse_compose` to `parser.py`**

In `src/lpp/parser.py`, change `_parse_lambda`'s fallback from `self._parse_or()` to `self._parse_compose()`:

```python
def _parse_lambda(self) -> Expression:
    # Lambda: ident -> expr  OR  ident,ident -> expr
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
    return self._parse_compose()
```

Add `_parse_compose` immediately after `_parse_lambda`:

```python
def _parse_compose(self) -> Expression:
    left = self._parse_or()
    while self.match(TokenType.AMP):
        self.advance()
        right = self._parse_or()
        left = Compose(left, right)
    return left
```

- [ ] **Step 5: Run parser tests**

```bash
pytest tests/test_parser.py::test_parse_compose tests/test_parser.py::test_parse_compose_chain -v
```

Expected: PASS

- [ ] **Step 6: Add `Compose` case to `transpiler.py`**

In `src/lpp/transpiler.py`, add a `Compose` case inside `_expr`, after the `Lambda` case:

```python
            case Lambda(params, body):
                return f"lambda {', '.join(params)}: {self._expr(body)}"
            case Compose(left, right):
                return f"(lambda *a, **kw: {self._expr(left)}({self._expr(right)}(*a, **kw)))"
```

- [ ] **Step 7: Run transpiler tests**

```bash
pytest tests/test_transpiler.py::test_compose tests/test_transpiler.py::test_compose_chain -v
```

Expected: PASS

- [ ] **Step 8: Add integration test**

Add to `tests/test_integration.py`:

```python
def test_function_composition():
    src = textwrap.dedent("""\
        fn double x
          x*2
        fn inc x
          x+1
        h=double&inc
        p(h(4))
    """)
    assert run_lpp(src) == "10"
```

`(double&inc)(4)` = `double(inc(4))` = `double(5)` = `10`.

- [ ] **Step 9: Run integration test**

```bash
pytest tests/test_integration.py::test_function_composition -v
```

Expected: PASS

- [ ] **Step 10: Run full suite**

```bash
pytest -v
```

Expected: all PASS

- [ ] **Step 11: Commit**

```bash
git add src/lpp/ast_nodes.py src/lpp/parser.py src/lpp/transpiler.py tests/test_parser.py tests/test_transpiler.py tests/test_integration.py
git commit -m "feat: function composition operator (&)"
```

---

## Task 2: Dotted Module Names in `use`

**Spec:** `use os.path`, `use collections.abc` should transpile to `import os.path`, `import collections.abc`. Currently the parser reads only one `IDENT` for the module name and raises `ParseError` on the `.`.

**Files:**
- Modify: `src/lpp/parser.py` (lines ~426–469, `_parse_use`)
- Test: `tests/test_parser.py`
- Test: `tests/test_transpiler.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_parser.py`:

```python
def test_parse_use_dotted():
    node = first("use os.path\n")
    from lpp.ast_nodes import UseStatement, UseImport
    assert isinstance(node, UseStatement)
    assert node.imports[0] == UseImport("os.path", None, None)

def test_parse_use_dotted_from():
    node = first("use os.path:join\n")
    from lpp.ast_nodes import UseStatement, UseImport
    assert node.imports[0] == UseImport("os.path", "join", None)
```

Add to `tests/test_transpiler.py`:

```python
def test_use_dotted():
    assert "import os.path" in py("use os.path\n")

def test_use_dotted_from():
    assert "from os.path import join" in py("use os.path:join\n")
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/test_parser.py::test_parse_use_dotted tests/test_transpiler.py::test_use_dotted -v
```

Expected: FAIL — `ParseError: Expected NEWLINE`

- [ ] **Step 3: Fix `_parse_use` in `parser.py`**

In `_parse_use`, replace the single `self.expect(TokenType.IDENT).value` module read with a dotted-name reader. The change is in the non-`from_module` branch:

```python
    def _parse_use(self) -> UseStatement:
        self.expect(TokenType.USE)
        imports = []
        from_module = None  # set when parsing module:item[,item] form
        while True:
            alias = None
            item = None
            if from_module is not None:
                # Continuation of a module:item,item2 form — read next item
                item = self.expect(TokenType.IDENT).value
                if self.match(TokenType.EQ):
                    self.advance()
                    alias = self.expect(TokenType.IDENT).value
                imports.append(UseImport(from_module, item, alias))
                if not self.match(TokenType.COMMA):
                    from_module = None
                    break
                self.advance()
                continue
            # Could be: ident, alias=module, module.sub, module:item, module.sub:item
            # Peek ahead for alias= pattern (only when no dots: np=numpy)
            if (self.peek_type() == TokenType.IDENT and
                    self.tokens[self.pos + 1].type == TokenType.EQ):
                alias = self.advance().value
                self.advance()  # skip =
            # Read dotted module name: ident (. ident)*
            module = self.expect(TokenType.IDENT).value
            while self.match(TokenType.DOT):
                self.advance()
                module += "." + self.expect(TokenType.IDENT).value
            if self.match(TokenType.COLON):
                self.advance()
                item = self.expect(TokenType.IDENT).value
                if self.match(TokenType.EQ):
                    self.advance()
                    alias = self.expect(TokenType.IDENT).value
                imports.append(UseImport(module, item, alias))
                # If followed by comma, subsequent idents are more items from same module
                if self.match(TokenType.COMMA):
                    self.advance()
                    from_module = module
                    continue
            else:
                imports.append(UseImport(module, item, alias))
            if not self.match(TokenType.COMMA):
                break
            self.advance()
        if self.match(TokenType.NEWLINE):
            self.advance()
        return UseStatement(imports)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_parser.py::test_parse_use_dotted tests/test_parser.py::test_parse_use_dotted_from tests/test_transpiler.py::test_use_dotted tests/test_transpiler.py::test_use_dotted_from -v
```

Expected: all PASS

- [ ] **Step 5: Run full suite to check no regressions**

```bash
pytest -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/lpp/parser.py tests/test_parser.py tests/test_transpiler.py
git commit -m "feat: dotted module names in use statement"
```

---

## Task 3: Dead Token Cleanup

**Problem:**
- `as` is in `KEYWORDS`, making it a reserved word that causes parse errors when used as an identifier (e.g. a variable named `as`). The parser never handles `TokenType.AS` — it was carried over from an early draft.
- `COLONCOLON` (`::`) is lexed but never parsed. It was added speculatively. Removing it makes `a::b` lex as `IDENT COLON COLON IDENT` (two colons), which is consistent and correct for now.

**Files:**
- Modify: `src/lpp/tokens.py`
- Modify: `src/lpp/lexer.py`
- Test: `tests/test_lexer.py`

- [ ] **Step 1: Write failing tests**

In `tests/test_lexer.py`, find the existing keyword-list test (it currently includes `TokenType.AS`). Also find the `a::b` test. Add a new test and note which ones need updating:

```python
def test_as_is_not_a_keyword():
    # 'as' should lex as IDENT after cleanup — it was never handled by the parser
    toks = [t for t in Lexer("as\n").tokenize() if t.type != TokenType.NEWLINE and t.type != TokenType.EOF]
    assert toks[0].type == TokenType.IDENT
    assert toks[0].value == "as"
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_lexer.py::test_as_is_not_a_keyword -v
```

Expected: FAIL — `as` currently lexes as `TokenType.AS`

- [ ] **Step 3: Remove `AS` from `KEYWORDS` in `tokens.py`**

In `src/lpp/tokens.py`, remove `AS` from the `KEYWORDS` dict:

```python
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
    "use": TokenType.USE,
    "alias": TokenType.ALIAS,
}
```

Also remove `AS = auto()` from `TokenType` and `COLONCOLON = auto()` from `TokenType`:

```python
class TokenType(Enum):
    # Keywords
    FN = auto()
    CLS = auto()
    IF = auto()
    EL = auto()
    FOR = auto()
    IN = auto()
    DO = auto()
    RET = auto()
    TRY = auto()
    ERR = auto()
    USE = auto()
    ALIAS = auto()
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    # Operators
    PIPE = auto()       # |
    ARROW = auto()      # ->
    AT = auto()         # @
    BANG = auto()       # !
    TILDE = auto()      # ~
    AMP = auto()        # &
    APPEND = auto()     # <<
    COLON = auto()      # :
    # Arithmetic / comparison
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    PLUSEQ = auto()
    MINUSEQ = auto()
    STAREQ = auto()
    SLASHEQ = auto()
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    DOT = auto()
    # Structural
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()
```

- [ ] **Step 4: Remove `::` from lexer MAP2**

In `src/lpp/lexer.py`, remove `"::": TokenType.COLONCOLON` from `MAP2`:

```python
MAP2 = {
    "->": TokenType.ARROW, "<<": TokenType.APPEND,
    "==": TokenType.EQEQ, "!=": TokenType.NEQ,
    "<=": TokenType.LTE,  ">=": TokenType.GTE,
    "+=": TokenType.PLUSEQ, "-=": TokenType.MINUSEQ,
    "*=": TokenType.STAREQ, "/=": TokenType.SLASHEQ,
}
```

- [ ] **Step 5: Update `test_lexer.py` to remove stale references**

The existing keyword list test currently includes `TokenType.AS`. Find this test and remove `TokenType.AS` from the expected list. Also find the `a::b` test and remove it (or update it to expect `IDENT COLON COLON IDENT`).

Specifically:

1. Remove `TokenType.AS` from the keyword types list in `test_keyword_tokens` (or whatever it's called — find it with `grep -n "AS" tests/test_lexer.py`).

2. Replace the `a::b` test body:

```python
def test_double_colon_is_two_colons():
    # :: is no longer a dedicated token — lexes as COLON COLON
    result = types("a::b")
    assert result == [TokenType.IDENT, TokenType.COLON, TokenType.COLON, TokenType.IDENT]
```

- [ ] **Step 6: Run lexer tests**

```bash
pytest tests/test_lexer.py -v
```

Expected: all PASS

- [ ] **Step 7: Run full suite**

```bash
pytest -v
```

Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add src/lpp/tokens.py src/lpp/lexer.py tests/test_lexer.py
git commit -m "chore: remove dead AS keyword and COLONCOLON token"
```

---

## Task 4: Structured Error Messages

**Goal:** `LexError` and `ParseError` carry structured `line` and `col` attributes. The CLI formats errors with a source pointer:

```
lpp: error at line 3, col 7: unexpected character '$'
  fn foo $bar
        ^
```

**Files:**
- Modify: `src/lpp/tokens.py` — add `col` field to `Token`
- Modify: `src/lpp/lexer.py` — track column, set `col` on Token, give `LexError` structured fields
- Modify: `src/lpp/parser.py` — give `ParseError` structured fields from token
- Modify: `src/lpp/cli.py` — format errors with source context
- Test: `tests/test_lexer.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_lexer.py`:

```python
def test_lex_error_has_line_and_col():
    from lpp.lexer import LexError
    try:
        Lexer('x = "unterminated\n').tokenize()
        assert False, "expected LexError"
    except LexError as e:
        assert e.line == 1
        assert e.col is not None
        assert e.col > 0

def test_token_has_col():
    tokens = Lexer("x = 42\n").tokenize()
    ident = tokens[0]
    assert ident.value == "x"
    assert ident.col == 1
    eq = tokens[1]
    assert eq.col == 3
```

Add to `tests/test_parser.py`:

```python
def test_parse_error_has_line_and_col():
    from lpp.parser import ParseError
    try:
        parse_prog("fn\n  x\n")  # fn with no name
        assert False, "expected ParseError"
    except ParseError as e:
        assert e.line is not None
        assert e.line >= 1
```

- [ ] **Step 2: Run to confirm failures**

```bash
pytest tests/test_lexer.py::test_lex_error_has_line_and_col tests/test_lexer.py::test_token_has_col -v
```

Expected: FAIL — `LexError` has no `line`/`col` attributes, `Token` has no `col` field

- [ ] **Step 3: Add `col` to `Token` in `tokens.py`**

```python
@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int = 0
```

- [ ] **Step 4: Track column in `Lexer`, give `LexError` structured fields**

Replace the existing `LexError` class and update `Lexer.__init__` and `add()` in `src/lpp/lexer.py`:

```python
class LexError(Exception):
    def __init__(self, message: str, line: int | None = None, col: int | None = None):
        super().__init__(message)
        self.line = line
        self.col = col
```

In `Lexer.__init__`, add `self.line_start = 0`:

```python
def __init__(self, source: str):
    self.source = source
    self.pos = 0
    self.line = 1
    self.line_start = 0
    self.tokens: list[Token] = []
    self.indent_stack: list[int] = [0]
```

Update `advance()` to track `line_start` when a newline is consumed:

```python
def advance(self) -> str:
    ch = self.source[self.pos]
    self.pos += 1
    if ch == "\n":
        self.line += 1
        self.line_start = self.pos
    return ch
```

Update `add()` to include `col`:

```python
def add(self, type: TokenType, value: str = "") -> None:
    col = self.pos - len(value) - self.line_start + 1
    self.tokens.append(Token(type, value, self.line, col))
```

Update all three `raise LexError(...)` calls to pass structured args:

```python
# In _scan_line (bad dedent):
raise LexError(
    f"unexpected indentation level {indent} at line {self.line}",
    line=self.line, col=indent + 1
)

# In _scan_string (unterminated):
raise LexError(
    f"unterminated string literal at line {self.line}",
    line=self.line, col=self.pos - self.line_start + 1
)

# In _scan_operator (unexpected char):
raise LexError(
    f"unexpected character {ch!r} at line {self.line}",
    line=self.line, col=self.pos - self.line_start
)
```

- [ ] **Step 5: Give `ParseError` structured fields in `parser.py`**

Replace the existing `ParseError` class:

```python
class ParseError(Exception):
    def __init__(self, message: str, line: int | None = None, col: int | None = None):
        super().__init__(message)
        self.line = line
        self.col = col
```

Update `expect()` to pass structured info:

```python
def expect(self, tt: TokenType) -> Token:
    tok = self.advance()
    if tok.type != tt:
        raise ParseError(
            f"expected {tt.name}, got {tok.type.name} ({tok.value!r})",
            line=tok.line, col=tok.col
        )
    return tok
```

Update `_parse_primary`'s terminal raise:

```python
raise ParseError(
    f"unexpected token {tok.type.name} ({tok.value!r})",
    line=tok.line, col=tok.col
)
```

Update `_parse_try`'s validation raise:

```python
tok = self.peek()
raise ParseError(
    "try block requires at least one err handler",
    line=tok.line, col=tok.col
)
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_lexer.py::test_lex_error_has_line_and_col tests/test_lexer.py::test_token_has_col tests/test_parser.py::test_parse_error_has_line_and_col -v
```

Expected: all PASS

- [ ] **Step 7: Update CLI to format errors with source context**

Replace the error-handling block in `src/lpp/cli.py`:

```python
import sys
import argparse
from .lexer import LexError
from .parser import ParseError
from . import compile_lpp


def _format_error(label: str, err: Exception, source: str) -> str:
    line = getattr(err, "line", None)
    col = getattr(err, "col", None)
    loc = f" at line {line}" if line else ""
    if col:
        loc += f", col {col}"
    lines = [f"lpp: {label}{loc}: {err}"]
    if line and source:
        src_lines = source.splitlines()
        if 0 < line <= len(src_lines):
            lines.append(f"  {src_lines[line - 1]}")
            if col:
                lines.append(f"  {' ' * (col - 1)}^")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lpp",
        description="L++ transpiler — compile .lpp files to Python",
    )
    parser.add_argument("file", help=".lpp source file")
    parser.add_argument("-o", "--output", help="write Python output to file instead of stdout")
    parser.add_argument("--run", action="store_true", help="execute transpiled Python immediately")
    args = parser.parse_args()

    try:
        with open(args.file) as f:
            source = f.read()
    except FileNotFoundError:
        print(f"lpp: error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        python_src = compile_lpp(source)
    except (LexError, ParseError) as e:
        print(_format_error("error", e, source), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"lpp: internal error: {e}", file=sys.stderr)
        sys.exit(1)

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

- [ ] **Step 8: Run full suite**

```bash
pytest -v
```

Expected: all PASS

- [ ] **Step 9: Manual smoke test**

```bash
echo 'fn' > /tmp/bad.lpp
lpp /tmp/bad.lpp
```

Expected output to stderr (something like):
```
lpp: error at line 1, col 1: expected IDENT, got EOF ('')
  fn
  ^
```

(Exact message depends on parser — verify it shows the source line and pointer.)

- [ ] **Step 10: Commit**

```bash
git add src/lpp/tokens.py src/lpp/lexer.py src/lpp/parser.py src/lpp/cli.py tests/test_lexer.py tests/test_parser.py
git commit -m "feat: structured error messages with line, col, and source pointer"
```

---

## Task 5: cl100k Tokenizer Validation Script

**Goal:** Validate that every L++ keyword and prelude alias is a single token in cl100k (the tokenizer used by GPT-4 / Claude). Report any that are multi-token so the keyword list can be reviewed.

**Files:**
- Create: `tools/validate_tokens.py`

**Prerequisite:** `pip install tiktoken`

- [ ] **Step 1: Create `tools/` directory and script**

Create `tools/validate_tokens.py`:

```python
#!/usr/bin/env python3
"""Validate that every L++ keyword and prelude alias is a single cl100k token.

Usage:
    pip install tiktoken
    python tools/validate_tokens.py
"""
import sys
try:
    import tiktoken
except ImportError:
    print("ERROR: tiktoken not installed. Run: pip install tiktoken")
    sys.exit(1)

# Add src/ to path so lpp imports work without installing
sys.path.insert(0, "src")
from lpp.tokens import KEYWORDS
from lpp.prelude import PRELUDE

enc = tiktoken.get_encoding("cl100k_base")

def check(label: str, items: list[str]) -> int:
    """Check items, print results, return count of multi-token failures."""
    failures = 0
    print(f"\n=== {label} ===")
    for item in sorted(items):
        token_ids = enc.encode(item)
        if len(token_ids) == 1:
            print(f"  OK       {item!r:10}  id={token_ids[0]}")
        else:
            print(f"  MULTI    {item!r:10}  ids={token_ids}  ({len(token_ids)} tokens)")
            failures += 1
    return failures

total_failures = 0
total_failures += check("Keywords", list(KEYWORDS.keys()))
total_failures += check("Prelude aliases", list(PRELUDE.keys()))

print(f"\n{'=' * 40}")
if total_failures == 0:
    print("All items are single tokens. ✓")
else:
    print(f"{total_failures} item(s) are NOT single tokens — consider renaming.")
    sys.exit(1)
```

- [ ] **Step 2: Run the script**

```bash
pip install tiktoken
python tools/validate_tokens.py
```

Expected: output listing each keyword and alias with OK/MULTI status. Any MULTI items should be noted as candidates for renaming in the language spec.

- [ ] **Step 3: Commit**

```bash
git add tools/validate_tokens.py
git commit -m "tools: cl100k tokenizer validation script"
```

---

## Self-Review

**Spec coverage:**

| Open item | Covered by |
|-----------|-----------|
| `&` function composition | Task 1 |
| Dotted module names (`use os.path`) | Task 2 |
| Dead `as` keyword + `::` token | Task 3 |
| Error messages for LLM feedback loops | Task 4 |
| cl100k tokenizer validation pass | Task 5 |

**Placeholder scan:** No TBDs, no vague steps, all code blocks are complete.

**Type consistency:**
- `Compose(left, right)` used consistently across Tasks 1 (ast_nodes, parser, transpiler).
- `Token` gains `col: int = 0` in Task 4 — the default of `0` means existing tests that don't check `col` continue to pass without modification.
- `LexError(message, line, col)` and `ParseError(message, line, col)` signatures are consistent between Tasks 4 steps and CLI usage.

---

**Deferred to brainstorming (need syntax design decisions before planning):**
- Decorator syntax — `@` is taken by self
- Generator / yield syntax
- Async / await syntax
- Bitwise OR alternative — `|` is taken by pipeline
- Formal grammar (BNF/PEG)
