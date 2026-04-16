# Architecture

**Analysis Date:** 2026-04-16

## Pattern Overview

**Overall:** Compiler/Transpiler Pipeline

L++ is a three-stage compiler that transforms terse L++ syntax into idiomatic Python source code:
1. **Tokenization** (Lexer) - Character stream → Token stream with indentation tracking
2. **Parsing** (Parser) - Token stream → Abstract Syntax Tree (AST)
3. **Code generation** (Transpiler) - AST → Valid Python source code

**Key Characteristics:**
- Source input is L++ `.lpp` files (custom terse syntax)
- Output is executable Python code
- Indentation-aware lexer (Python-style blocks)
- Recursive-descent parser with operator precedence
- Direct AST-to-source transpilation (no intermediate representation)

## Layers

**Lexer (`src/lpp/lexer.py`):**
- Purpose: Tokenize source code and track indentation level
- Location: `src/lpp/lexer.py`
- Contains: Character scanning, token creation, indent/dedent tracking
- Depends on: `tokens.py` (TokenType enum, KEYWORDS map)
- Used by: Parser initialization
- Key method: `tokenize()` → `list[Token]`

**Parser (`src/lpp/parser.py`):**
- Purpose: Build Abstract Syntax Tree from token stream
- Location: `src/lpp/parser.py`
- Contains: Recursive-descent expression/statement parsing, operator precedence handling
- Depends on: `lexer.py`, `tokens.py`, `ast_nodes.py`
- Used by: Transpiler, compilation pipeline
- Key method: `parse()` → `Program` (AST root)

**AST Layer (`src/lpp/ast_nodes.py`):**
- Purpose: Define immutable data structures for syntax tree
- Location: `src/lpp/ast_nodes.py`
- Contains: Dataclass definitions for all expression and statement types
- Depends on: Python dataclasses module
- Used by: Parser (builds nodes), Transpiler (traverses nodes)

**Transpiler (`src/lpp/transpiler.py`):**
- Purpose: Transform AST into Python source code
- Location: `src/lpp/transpiler.py`
- Contains: AST pattern matching and Python code generation
- Depends on: `ast_nodes.py`, `prelude.py`
- Used by: Compilation API
- Key method: `transpile(program: Program)` → `str` (Python source)

**Tokens (`src/lpp/tokens.py`):**
- Purpose: Define token types and keyword mappings
- Location: `src/lpp/tokens.py`
- Contains: TokenType enum (70+ variants), KEYWORDS dict, Token dataclass
- Depends on: Python enum module
- Used by: Lexer, Parser

**Prelude (`src/lpp/prelude.py`):**
- Purpose: Auto-inject alias table at top of every compiled file
- Location: `src/lpp/prelude.py`
- Contains: Prelude mapping dict (30+ aliases like `p→print`, `l→len`)
- Depends on: None
- Used by: Transpiler (called during `transpile()`)

**CLI (`src/lpp/cli.py`):**
- Purpose: Command-line interface for lpp compiler
- Location: `src/lpp/cli.py`
- Contains: argparse setup, file I/O, error formatting
- Depends on: `__init__.py` (compile_lpp), lexer/parser (error types)
- Used by: Entry point `lpp` command

**Public API (`src/lpp/__init__.py`):**
- Purpose: Expose primary compilation function
- Location: `src/lpp/__init__.py`
- Contains: `compile_lpp(source: str) → str` wrapper
- Depends on: All internal modules
- Used by: CLI, tests, external consumers

## Data Flow

**Compilation Pipeline:**

```
Source Code (.lpp)
     ↓
[Lexer.tokenize()]
     ↓
Token Stream (list[Token])
     ↓
[Parser.parse()]
     ↓
Program AST
     ↓
[Transpiler.transpile()]
     ↓
Python Source Code
     ↓
[inject_prelude()]
     ↓
Final Python Code
```

**Example - FizzBuzz:**

```
Input: for i in r(1,101)
         if i%15==0
           p("FizzBuzz")

Lexer:   [FOR, IDENT(i), IN, IDENT(r), LPAREN, NUMBER(1), COMMA, NUMBER(101), RPAREN, NEWLINE, INDENT, IF, ...]

Parser:  Program(
           body=[
             ForStatement(
               targets=['i'],
               iterable=Call(Name('r'), [NumberLiteral(1), NumberLiteral(101)]),
               body=[IfStatement(...), ...]
             )
           ]
         )

Transpiler:
         for i in r(1, 101):
             if i % 15 == 0:
                 p("FizzBuzz")

Prelude injected:
         p = print
         r = range
         ...
         for i in r(1, 101):
             if i % 15 == 0:
                 p("FizzBuzz")
```

**State Management:**
- Lexer maintains `indent_stack` (list of column positions) to emit INDENT/DEDENT tokens
- Parser maintains `pos` (current token index) for lookahead/backtracking
- Transpiler is stateless; generates code directly from AST via pattern matching
- No global state shared between stages

## Key Abstractions

**Expression Types:**
- **Binary operators:** `BinOp` (arithmetic, comparison, logical)
- **Unary operators:** `UnaryOp` (negation, logical not)
- **Calls:** `Call` (function calls with args/kwargs), `ZeroArgCall` (trailing `!`)
- **Pipeline:** `Pipeline` (chained `|` operators)
- **Lambda:** `Lambda` (inline functions with `->` syntax)
- **Composition:** `Compose` (function composition with `&`)
- **Literals:** `NumberLiteral`, `StringLiteral`, `ListLiteral`, `DictLiteral`
- **Self reference:** `SelfAttr` (`@attr` for `self.attr`)
- **Attribute/subscript:** `Attribute`, `Subscript`

**Statement Types:**
- Control flow: `IfStatement`, `ForStatement`, `DoStatement`, `TryStatement`, `WithStatement`
- Functions/classes: `FunctionDef`, `ClassDef`
- Assignments: `Assignment`, `AugAssignment`, `UnpackAssignment`, `AppendStatement`
- Imports: `UseStatement` (unified import syntax)
- Jumps: `RetStatement`, `BreakStatement`, `ContinueStatement`
- Declarations: `GlobalStatement`, `NonlocalStatement`
- Other: `RaiseStatement`, `ExprStatement`

**String Interpolation:**
- Raw string contains `$expr$` markers
- Parser intercepts string parsing, tokenizes/parses expressions within markers
- Transpiler emits Python f-string equivalent

## Entry Points

**CLI Entry (`src/lpp/cli.py:main()`):**
- Location: `src/lpp/cli.py:main()`
- Triggers: Shell invocation `lpp program.lpp`
- Responsibilities:
  - Parse command-line arguments (file, -o/--output, --run)
  - Read `.lpp` source file
  - Call `compile_lpp()`
  - Handle LexError/ParseError with formatted messages
  - Write output to file or stdout
  - Execute compiled code if `--run` flag

**API Entry (`src/lpp/__init__.py:compile_lpp()`):**
- Location: `src/lpp/__init__.py`
- Triggers: Direct import/call by tests or external code
- Responsibilities:
  - Orchestrate Lexer → Parser → Transpiler pipeline
  - Handle ImportError gracefully (stub if modules missing)
  - Return final Python source code

## Error Handling

**Strategy:** Exceptions propagate with location information (line, col)

**Patterns:**

1. **Lexer errors (`LexError`):**
   - Raised by `_scan_string()`, indentation validation, numeric parsing
   - Attributes: `message`, `line`, `col`
   - Example: Unterminated string, invalid indentation
   - Location: `src/lpp/lexer.py`

2. **Parser errors (`ParseError`):**
   - Raised throughout recursive descent (`expect()`, `_parse_*()` methods)
   - Attributes: `message`, `line`, `col`
   - Example: Expected token mismatch, unexpected token
   - Location: `src/lpp/parser.py`

3. **CLI error formatting (`_format_error()`):**
   - Catches `LexError`/`ParseError` in CLI
   - Formats: `lpp: error at line X, col Y: message`
   - Shows source line with caret pointing to error position
   - Location: `src/lpp/cli.py:_format_error()`

4. **Transpiler errors:**
   - Raises `NotImplementedError` for unhandled AST node types
   - Pattern-match exhaustiveness guards via `case _`
   - Location: `src/lpp/transpiler.py:_stmt()`, `_expr()`

## Cross-Cutting Concerns

**Logging:** Not used. Errors only emit to stderr via print/sys.stderr.

**Validation:**
- Lexer: Validates string termination, indentation levels, number format
- Parser: Validates token sequences, construct grammar compliance
- Transpiler: Implicit via pattern-match exhaustiveness

**Implicit Return:**
- Parser creates normal statements throughout
- Transpiler special-cases last statement in function body
- If `ExprStatement`, wraps with `return` prefix
- Otherwise emits as-is (e.g., explicit `return`, control flow)
- Location: `src/lpp/transpiler.py:_fn()` lines 115-122

**Method Handling (@ prefix):**
- Parser detects `@` before function name in `def`, sets `is_method=True`
- Transpiler injects `self` as first parameter
- Dunder name detection: if method name in `_DUNDER_NAMES`, wraps with `__`
- Examples: `def @init` → `def __init__(self)`, `def @add` → `def __add__(self, ...)`
- Location: `src/lpp/parser.py:_parse_function()`, `src/lpp/transpiler.py:_fn()` lines 110
