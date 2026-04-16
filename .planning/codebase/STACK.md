# Technology Stack

**Analysis Date:** 2026-04-16

## Languages

**Primary:**
- Python 3.11+ - Main language for the transpiler implementation and compiled output
  - Used in: `src/lpp/` all modules, `tests/` all test files, `cli.py`

## Runtime

**Environment:**
- Python 3.11 or higher (enforced in `pyproject.toml`)
- No virtual environment manager configured; uses standard pip/setuptools

**Package Manager:**
- pip (with optional uv support)
- Build backend: setuptools 68+
- Lockfile: Not present (no `requirements.txt`, `poetry.lock`, or `Pipfile`)

## Frameworks

**Core:**
- setuptools 68+ - Build system and package distribution (`pyproject.toml`)

**Testing:**
- pytest - Test framework and runner
  - Location: Tests in `tests/` directory (e.g., `test_lexer.py`, `test_parser.py`, `test_transpiler.py`, `test_integration.py`, `test_prelude.py`)
  - Config: `pyproject.toml` with `[tool.pytest.ini_options]` defining `testpaths` and `pythonpath`
  - Entry: `pytest` command runs all tests in `tests/` directory

**Build/Dev:**
- argparse - Command-line interface
  - Used in: `src/lpp/cli.py` for argument parsing (file input, output file, --run flag)

## Key Dependencies

**Critical (Standard Library Only):**
- No external third-party dependencies
- All imports are from Python standard library only:
  - `dataclasses` - AST node definitions (`src/lpp/ast_nodes.py`)
  - `enum` - TokenType enum (`src/lpp/tokens.py`)
  - `argparse` - CLI argument handling (`src/lpp/cli.py`)
  - `sys` - System operations (`src/lpp/cli.py`)
  - `typing` - Type hints throughout codebase

## Configuration

**Environment:**
- No `.env` files or environment variable configuration required
- All configuration through CLI arguments and `pyproject.toml`

**Build:**
- `pyproject.toml` - Single source of truth for project metadata, build system, and pytest configuration
  - Entry point: `lpp = "lpp.cli:main"` creates `lpp` CLI command
  - Package discovery: setuptools auto-finds packages in `src/`

**Development:**
- No additional dev dependencies (pytest must be installed separately)
- No type checker configuration (no mypy.ini, pyproject.toml type checker settings)
- No linter configuration (no .eslintrc, .pylintrc, etc.)
- No formatter configuration (no .prettierrc, black config, etc.)

## Platform Requirements

**Development:**
- Python 3.11+
- pip or uv package manager
- Standard Unix/Windows shell for running `lpp` CLI

**Production:**
- Python 3.11+
- Deployable as PyPI package or editable install
- No platform-specific dependencies

## Installation

**From Source:**
```bash
pip install -e .          # Editable install with setuptools
# or
uv pip install -e .       # With uv package manager
```

**This installs:**
- `lpp` command-line entry point
- `lpp` package with all submodules (lexer, parser, transpiler, cli, etc.)

## Test Configuration

- Test runner: pytest
- Test discovery: `tests/` directory
- Python path for tests: `src/` (allows `import lpp` directly)
- Fixtures: Defined in `tests/conftest.py` with pytest plugin

---

*Stack analysis: 2026-04-16*
