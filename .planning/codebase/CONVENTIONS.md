# Coding Conventions

**Analysis Date:** 2026-04-16

## Naming Patterns

**Files:**
- Lowercase with underscores: `lexer.py`, `ast_nodes.py`, `transpiler.py`
- Error classes end with `Error`: `LexError`, `ParseError` in `lexer.py` and `parser.py`
- Test files follow `test_<module>.py` pattern: `test_lexer.py`, `test_parser.py`

**Classes:**
- PascalCase for all classes: `Lexer`, `Parser`, `Transpiler`, `Token`, `TokenType`
- AST node classes are PascalCase: `BinOp`, `FunctionDef`, `ClassDef`, `IfStatement`
- Union type aliases are descriptive: `Expression`, `Statement` in `ast_nodes.py`

**Functions:**
- snake_case for all functions and methods: `tokenize()`, `parse()`, `transpile()`
- Private/internal methods prefixed with underscore: `_scan_token()`, `_parse_expression()`, `_expr()`, `_stmt()`
- Exception handler names use try-block semantics: `_parse_expression()`, `_try_parse_unpack_targets()`
- Helper methods that check conditions start with `is_` or `_try_`: `_try_parse_unpack_targets()` in `parser.py:632`

**Variables:**
- Lowercase snake_case: `source`, `tokens`, `pos`, `line`, `indent_stack`
- Short abbreviations common in context: `tt` for token type, `col` for column, `src` for source
- Enum members in UPPERCASE: `TokenType.INDENT`, `TokenType.DEDENT`, `TokenType.NUMBER`

**Constants:**
- UPPERCASE with underscores: `KEYWORDS` dict in `tokens.py`, `PRELUDE` dict in `prelude.py`
- Configuration constants: `INDENT = "    "` in `transpiler.py:5`, `_DUNDER_NAMES` frozenset in `transpiler.py:81`

## Code Style

**Formatting:**
- Standard Python conventions (implied, no formatter specified in config)
- 4-space indentation throughout
- Lines generally under 100 characters (observed in all modules)
- No trailing whitespace or extra blank lines

**Linting:**
- No explicit linter configuration detected in pyproject.toml
- Code follows PEP 8 conventions implicitly
- Type hints used throughout: `list[Token]`, `dict[str, TokenType]`, `Expression | None`

## Import Organization

**Order:**
1. Standard library imports: `import sys`, `import argparse`, `from dataclasses import dataclass`
2. Relative imports (own modules): `from .tokens import Token, TokenType, KEYWORDS`
3. Exception classes defined in same file

**Path Aliases:**
- No path aliases detected; uses relative imports consistently: `from .lexer import Lexer`, `from .ast_nodes import *`
- Imports are generally explicit except for AST nodes which use wildcard: `from .ast_nodes import *` in `parser.py:4`

**Import Style:**
- Specific imports preferred: `from .tokens import Token, TokenType, KEYWORDS`
- Wildcard imports only for AST nodes (large union type): `from .ast_nodes import *` in `parser.py:4` and `transpiler.py:2`

## Error Handling

**Exception Classes:**
- Custom exceptions inherit from `Exception`
- Exceptions carry location information: `LexError` and `ParseError` in `lexer.py:4` and `parser.py:6`
- Exception constructors accept message and optional line/col info

**Pattern:**
```python
class LexError(Exception):
    def __init__(self, message: str, line: int | None = None, col: int | None = None):
        super().__init__(message)
        self.line = line
        self.col = col
```

**Error Raising:**
- Raised with context: `raise LexError("unterminated string literal", line=self.line, col=string_col)` in `lexer.py:129`
- Compound conditions for validation before raising: Check indentation levels, token types before raising errors

**Error Handling in CLI:**
- Caught at top level in `cli.py:43-48`
- Formatted with location information via `_format_error()` helper
- Exits with code 1 on error

## Logging

**Framework:** `print()` only; no logging framework used

**Patterns:**
- Error messages use `sys.stderr` for logging: `print(..., file=sys.stderr)` in `cli.py`
- Format: "program_name: error_type: message" (e.g., "lpp: error: file not found")
- Location info appended to errors: "at line 5, col 12"
- Source context displayed: Show problematic line + caret pointer

## Comments

**When to Comment:**
- Sparingly used; code is self-documenting through good naming
- Comments appear for non-obvious logic or state transitions
- E.g., comment on blank line handling in `lexer.py:52`, operator mapping in `lexer.py:160-177`

**Documentation Comments:**
- Docstrings on complex public functions: `_parse_string_literal()` in `parser.py:48-49`
- Docstrings explain "what" and "why": "Parse a raw string value containing $...$ interpolation markers."
- No JSDoc/TSDoc (Python codebase)

**Examples:**
```python
def _parse_string_literal(self, raw: str) -> StringLiteral:
    """Parse a raw string value containing $...$ interpolation markers."""

# Inline comment on tricky logic:
# Blank line or comment-only line — skip without emitting NEWLINE
if self.peek() in ("", "\n", "#"):
```

## Function Design

**Size:**
- Functions generally 20-50 lines; longer methods broken into smaller helpers
- `_scan_token()` in `lexer.py:87` is concise, delegates to `_scan_string()`, `_scan_number()`, etc.
- Complex parsing methods use helper pattern: `_try_parse_unpack_targets()` extracted in `parser.py:632`

**Parameters:**
- Generally 1-3 parameters; `self` for methods
- Depth/indentation passed as int for recursive code generation: `_stmt(node, depth)` in `transpiler.py:15`

**Return Values:**
- Explicit return types in signature: `-> list[Token]`, `-> Expression`, `-> str`
- Early returns for guard conditions: `if ch == " ": self.pos += 1; return`

## Module Design

**Exports:**
- No `__all__` declaration; public API inferred from naming (no leading underscore)
- Module docstrings absent; imports are clear

**Barrel Files:**
- No barrel files; `__init__.py` is minimal, importing core classes: `from .lexer import Lexer` etc.
- Top-level API: `compile_lpp(source: str) -> str` in `__init__.py:7`

**Pattern for Large Modules:**
- Code organized by concern within file (e.g., `transpiler.py` splits statements from expressions)
- Comments separate sections: `# --- Statements ---`, `# --- Expressions ---` in `transpiler.py:13, 178`

## Type Hints

**Usage:**
- Type hints on all function signatures: `def tokenize(self) -> list[Token]:`
- Union types using `|` syntax: `line: int | None`, `target: str | Expression`
- Dataclass field hints required

**Patterns:**
- Generic types spelled out: `list[Token]`, `dict[str, TokenType]`
- Union aliases at module level: `Expression = Union[...]` in `ast_nodes.py:5`

## Match Statements

**Python 3.10+ Pattern Matching:**
- Used heavily in `transpiler.py` for AST node dispatch
- Example: `match node:` followed by `case ClassName(): ...`
- Pattern matching replaces complex if-elif chains

**Example from transpiler.py:15-78:**
```python
match node:
    case FunctionDef():
        return self._fn(node, depth)
    case ClassDef():
        return self._cls(node, depth)
    case Assignment(target, value):
        tgt = target if isinstance(target, str) else self._expr(target)
        return f"{pad}{tgt} = {self._expr(value)}"
```

---

*Convention analysis: 2026-04-16*
