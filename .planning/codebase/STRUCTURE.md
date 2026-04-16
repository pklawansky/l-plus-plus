# Codebase Structure

**Analysis Date:** 2026-04-16

## Directory Layout

```
l-plus-plus/
├── .claude/                # Claude settings
├── .planning/              # GSD planning documents
│   └── codebase/          # This directory
├── .pytest_cache/         # pytest cache (generated)
├── .worktrees/            # git worktree directories
├── docs/                  # Documentation
│   └── superpowers/
│       ├── plans/
│       └── specs/
├── examples/              # Example .lpp programs
│   └── fizzbuzz.lpp
├── src/lpp/               # Main compiler package
│   ├── __init__.py       # Public API: compile_lpp()
│   ├── cli.py            # Command-line interface
│   ├── lexer.py          # Tokenizer with indent tracking
│   ├── parser.py         # Recursive-descent parser
│   ├── ast_nodes.py      # AST node dataclasses
│   ├── transpiler.py     # AST → Python code generator
│   ├── tokens.py         # Token types and keywords
│   └── prelude.py        # Alias injection (p→print, etc.)
├── tests/                # Test suite
│   ├── conftest.py       # pytest configuration
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_transpiler.py
│   ├── test_integration.py
│   └── test_prelude.py
├── tools/                # Developer utilities
├── pyproject.toml        # Project metadata (Python 3.11+, setuptools)
├── .gitignore
└── README.md
```

## Directory Purposes

**`src/lpp/`:**
- Purpose: Main compiler implementation
- Contains: Core lexer, parser, AST definitions, transpiler
- Key files: `lexer.py`, `parser.py`, `ast_nodes.py`, `transpiler.py`

**`tests/`:**
- Purpose: Test suite with 100% lexer/parser coverage
- Contains: Unit tests for each stage, integration tests
- Key files: `test_lexer.py`, `test_parser.py`, `test_transpiler.py`, `test_integration.py`

**`examples/`:**
- Purpose: Example L++ programs demonstrating features
- Contains: `.lpp` source files
- Key file: `fizzbuzz.lpp`

**`docs/superpowers/`:**
- Purpose: Superpower specifications and implementation plans
- Contains: Feature specs in `specs/`, phase plans in `plans/`

**`tools/`:**
- Purpose: Developer scripts and utilities
- Contains: Development-only code (not part of main package)

## Key File Locations

**Entry Points:**
- `src/lpp/__init__.py`: Public API (`compile_lpp(source: str) → str`)
- `src/lpp/cli.py`: CLI entry point (registered as `lpp` command via setuptools)

**Configuration:**
- `pyproject.toml`: Project metadata, Python version requirement, test config
- `src/lpp/tokens.py`: Keyword list and token type definitions

**Core Logic:**
- `src/lpp/lexer.py`: Tokenization with indent/dedent tracking
- `src/lpp/parser.py`: Grammar parsing, expression precedence, string interpolation
- `src/lpp/ast_nodes.py`: AST node definitions (30+ dataclasses)
- `src/lpp/transpiler.py`: AST-to-Python code generation

**Support:**
- `src/lpp/prelude.py`: Alias injection (30+ built-in aliases)

**Testing:**
- `tests/conftest.py`: pytest fixture (`lpp` compilation function)
- `tests/test_lexer.py`: Lexer unit tests
- `tests/test_parser.py`: Parser unit tests
- `tests/test_transpiler.py`: Transpiler unit tests
- `tests/test_integration.py`: End-to-end compilation tests
- `tests/test_prelude.py`: Prelude injection tests

## Naming Conventions

**Files:**
- `test_*.py`: Test modules
- `*.lpp`: L++ source files
- `*.py`: Python source (following PEP8)

**Directories:**
- `src/` prefix: Source code (standard Python packaging)
- `tests/` prefix: Test code (pytest convention)
- UPPERCASE with underscore: Special directories (`.planning`, `.pytest_cache`)

**Functions:**
- `_private()`: Single leading underscore for internal methods
- `__dunder__()`: Dunder names preserved in transpiler (e.g., `__init__`)
- `snake_case`: Standard Python convention

**Classes:**
- `PascalCase`: Standard Python convention
- AST nodes use `PascalCase` with suffix (e.g., `FunctionDef`, `IfStatement`, `BinOp`)
- Error classes use `PascalCase` with "Error" suffix (e.g., `LexError`, `ParseError`)

**Variables:**
- `snake_case`: Standard Python convention
- `SCREAMING_SNAKE_CASE`: Module-level constants (e.g., `KEYWORDS`, `PRELUDE`)

## Where to Add New Code

**New Feature (e.g., new operator):**
1. Add token type to `src/lpp/tokens.py:TokenType`
2. Update keyword/symbol scanning in `src/lpp/lexer.py:_scan_token()`
3. Add AST node to `src/lpp/ast_nodes.py` if needed
4. Add parser rule in `src/lpp/parser.py` (find appropriate precedence level)
5. Add transpiler case in `src/lpp/transpiler.py:_expr()` or `_stmt()`
6. Write tests: `tests/test_lexer.py`, `tests/test_parser.py`, `tests/test_transpiler.py`
7. Add integration example in `tests/test_integration.py`

**New Built-in Alias (e.g., add `ax→axis`):**
1. Add entry to `src/lpp/prelude.py:PRELUDE` dict
2. Write test in `tests/test_prelude.py`

**New Test:**
- Unit tests: `tests/test_*.py` (corresponding module)
- Integration tests: `tests/test_integration.py`
- Use pytest fixture from `tests/conftest.py` to compile L++ code

**CLI Enhancement:**
- Modify `src/lpp/cli.py:main()` and argparse setup
- Test in `tests/test_integration.py` (integration layer)

## Special Directories

**`.planning/codebase/`:**
- Purpose: GSD mapping documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (by GSD mapper agent)
- Committed: Yes

**`.pytest_cache/`:**
- Purpose: pytest internals cache
- Generated: Yes
- Committed: No (in .gitignore)

**`.worktrees/`:**
- Purpose: git worktree directories
- Generated: Yes (developer only)
- Committed: No (in .gitignore)

**`src/lpp.egg-info/`:**
- Purpose: setuptools package metadata
- Generated: Yes
- Committed: No (in .gitignore)

## Import Structure

**Public API:**
```python
from lpp import compile_lpp
python_code = compile_lpp(lpp_source)
```

**Internal imports (within package):**
- Lexer → `from .tokens import Token, TokenType, KEYWORDS`
- Parser → `from .tokens import Token, TokenType` + `from .lexer import Lexer` + `from .ast_nodes import *`
- Transpiler → `from .ast_nodes import *` + `from .prelude import inject_prelude`
- CLI → `from .lexer import LexError` + `from .parser import ParseError` + `from . import compile_lpp`

**No circular imports:** Dependency chain is linear: tokens → lexer/parser/ast_nodes → transpiler/cli → __init__

## Test Organization

**Test file structure:**
```
tests/
├── test_lexer.py          # ~400 lines: tokenization, indentation, edge cases
├── test_parser.py         # ~600 lines: expressions, statements, error recovery
├── test_transpiler.py     # ~300 lines: code generation for all AST nodes
├── test_integration.py    # ~200 lines: end-to-end scenarios
├── test_prelude.py        # ~50 lines: alias injection verification
└── conftest.py            # pytest fixture: compile_lpp() wrapper
```

**Test pattern:**
```python
def test_feature(lpp):
    result = lpp("source code")
    assert "expected_output" in result
```

**Running tests:**
```bash
pytest                    # Run all tests
pytest -v               # Verbose
pytest tests/test_lexer.py  # Single module
pytest -k "keyword"     # Filter by name
```

## Build & Package

**Development install:**
```bash
pip install -e .        # Editable install from source
```

**Entry point:**
- Configured in `pyproject.toml:[project.scripts]`
- Name: `lpp`
- Target: `lpp.cli:main()`
- Makes `lpp` command available globally after install

**Requirements:**
- Python 3.11+ (specified in `pyproject.toml:requires-python`)
- No external dependencies (standard library only)

## File Size Reference

**Source files (approximate lines):**
- `parser.py`: ~660 lines (largest; complex recursive descent)
- `transpiler.py`: ~250 lines
- `lexer.py`: ~200 lines
- `ast_nodes.py`: ~150 lines
- `tokens.py`: ~105 lines
- `cli.py`: ~62 lines
- `prelude.py`: ~52 lines
- `__init__.py`: ~17 lines

**Test files (approximate lines):**
- `test_parser.py`: ~600 lines
- `test_lexer.py`: ~400 lines
- `test_transpiler.py`: ~300 lines
- `test_integration.py`: ~200 lines
- `test_prelude.py`: ~50 lines
- `conftest.py`: ~10 lines
