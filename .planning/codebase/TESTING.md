# Testing Patterns

**Analysis Date:** 2026-04-16

## Test Framework

**Runner:**
- pytest 9.0.2
- Config: `pyproject.toml`

**Test Configuration (pyproject.toml):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**Run Commands:**
```bash
pytest tests/                    # Run all tests
pytest tests/ -v                 # Verbose mode
pytest tests/test_lexer.py      # Run specific test file
pytest tests/test_lexer.py::test_token_creation  # Run specific test
```

**Assertion Library:**
- Built-in `assert` statements; no custom assertion library

## Test File Organization

**Location:**
- Co-located in separate `tests/` directory (not alongside source)
- Mirror structure to source layout (not strict, but files match module names)

**Naming:**
- Pattern: `test_<module>.py`
- Examples: `test_lexer.py`, `test_parser.py`, `test_transpiler.py`, `test_integration.py`

**File Structure:**
```
tests/
├── conftest.py          # Pytest fixtures
├── test_lexer.py        # Lexer unit tests
├── test_parser.py       # Parser unit tests
├── test_transpiler.py   # Transpiler unit tests
├── test_integration.py  # End-to-end tests
└── test_prelude.py      # Prelude functionality
```

**Coverage:** 161 tests total
- `test_integration.py`: 14 tests
- `test_lexer.py`: 30 tests
- `test_parser.py`: 70+ tests
- `test_transpiler.py`: 30+ tests
- `test_prelude.py`: 3 tests

## Test Structure

**Suite Organization:**
```python
import pytest
from lpp.lexer import Lexer
from lpp.tokens import TokenType, Token

def tokenize(src: str) -> list[Token]:
    """Helper function for repeated operation."""
    return Lexer(src).tokenize()

def types(src: str) -> list[TokenType]:
    """Extract token types from source, excluding EOF."""
    return [t.type for t in tokenize(src) if t.type != TokenType.EOF]

def test_token_creation():
    t = Token(TokenType.IDENT, "foo", line=1)
    assert t.type == TokenType.IDENT
```

**Test Organization Patterns:**
1. **Helpers at module level:** `tokenize()`, `types()`, `parse_expr()`, `run_lpp()` defined before tests
2. **No test classes:** All functions are module-level `test_*` functions
3. **Clear test names:** `test_keywords`, `test_identifiers`, `test_string_literal` etc.

**Patterns:**
- **Setup:** Usually done inline or via fixture (see conftest.py)
- **Teardown:** File cleanup in integration tests (tempfile cleanup in `test_integration.py:19`)
- **Assertion pattern:** Direct `assert` statements, simple comparisons

## Mocking

**Framework:** None detected; no unittest.mock usage

**Patterns:**
- No mocking; tests use real implementations
- For integration tests, actual Python code is executed: `subprocess.run()` in `test_integration.py:11-17`

**What is NOT Mocked:**
- Lexer, Parser, Transpiler all use real implementations
- File I/O is tested with actual temp files (not mocked)
- Subprocess execution is real in integration tests

**Test Doubles:**
- Helper functions used instead of mocks: `tokenize()`, `parse_expr()`, `run_lpp()`
- These simplify test code without introducing mock complexity

## Fixtures

**conftest.py Location:** `tests/conftest.py`

**Fixture Pattern:**
```python
import pytest
from lpp import compile_lpp

@pytest.fixture
def lpp():
    def _compile(source: str) -> str:
        return compile_lpp(source)
    return _compile
```

**Fixture Usage:**
- `lpp` fixture available to all tests but rarely used directly
- Instead, tests create helper functions like `py()` in `test_transpiler.py:5-11`

## Test Data and Factories

**Test Data Pattern:**
```python
def types(src: str) -> list[TokenType]:
    return [t.type for t in tokenize(src) if t.type != TokenType.EOF]

def test_keywords():
    assert types("def") == [TokenType.DEF]
    assert types("if elif else for in while return try except use alias class") == [
        TokenType.IF, TokenType.ELIF, TokenType.ELSE, ...
    ]
```

**Inline Data Creation:**
- Literal strings as test input
- Expected output hardcoded in assertions
- No external test data files

**AST Node Factories:**
- Direct instantiation: `Token(TokenType.IDENT, "foo", line=1)`
- Or via parser: `parse_expr("42")` returns `NumberLiteral(42)`

## Coverage

**Requirements:** Not enforced (no coverage configuration in pyproject.toml)

**View Coverage:**
```bash
pytest --cov=src --cov-report=html tests/
```
(Command inferred; not currently configured)

**Observed Coverage:**
- 161 passing tests across all modules
- Integration tests execute end-to-end compilation + execution
- Good coverage of error cases: `test_unterminated_string_raises()`, `test_lex_error_has_line_and_col()`

## Test Types

**Unit Tests (majority):**
- Focus on individual functions: `test_token_creation()`, `test_keywords()`
- Test single responsibility: Lexer tests in `test_lexer.py`, Parser in `test_parser.py`
- Scope: Input → output assertions on specific component

**Integration Tests:**
- File: `test_integration.py`
- Scope: Full pipeline (lex → parse → transpile → execute)
- Method: Compile L++ source to Python, execute via subprocess, capture output
- Examples: `test_hello_world()`, `test_function_call()`, `test_class()`

**AST/Transpiler Tests:**
- `test_parser.py`: Parse source → AST node assertions
- `test_transpiler.py`: AST → Python string output assertions
- Use helper `py()` to strip prelude for clarity

**Error Path Tests:**
- `test_unterminated_string_raises()` in `test_lexer.py:69`
- `test_lex_error_has_line_and_col()` in `test_lexer.py:87`
- Verify exceptions include location info

## Common Patterns

**Async Testing:**
Not applicable; codebase is synchronous.

**Error Testing:**
```python
def test_unterminated_string_raises():
    from lpp.lexer import LexError
    with pytest.raises(LexError, match="[Uu]nterminated"):
        tokenize('"hello')

def test_lex_error_has_line_and_col():
    from lpp.lexer import LexError
    try:
        Lexer('"unterminated\n').tokenize()
        assert False, "expected LexError"
    except LexError as e:
        assert e.line == 1
        assert e.col is not None
        assert e.col > 0
```

**AST Node Equality Testing:**
```python
def test_parse_number():
    assert parse_expr("42") == NumberLiteral(42)

def test_parse_binop_add():
    assert parse_expr("x+y") == BinOp(Name("x"), "+", Name("y"))
```
(Works because AST nodes are dataclasses with auto-generated `__eq__`)

**Transpiler Output Testing:**
```python
def py(src: str) -> str:
    """Compile L++ and strip prelude for test clarity."""
    full = compile_lpp(src)
    # Strip prelude lines (up to first blank line after prelude)
    lines = full.split("\n")
    start = next(i for i, l in enumerate(lines) if l == "") + 1
    return "\n".join(lines[start:]).strip()

def test_binop():
    assert py("x+y\n") == "x + y"
```

**Subprocess Execution for Integration:**
```python
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
```

## Test Execution Flow

**Full Test Run:**
- 161 tests pass (as of last check)
- No skipped or xfail tests
- Tests execute sequentially
- No database setup/teardown

---

*Testing analysis: 2026-04-16*
