# L++ Work Priorities

*Last updated: 2026-04-18 (session 6)*

---

## Highest Return

### 1. String escape handling — `[ DONE ]`
`_escape_str_content` implemented in `transpiler.py:234-251`, `_string()` uses it on all paths. 7 transpiler tests passing. Was already complete before this session.

### 2. Parser error coverage — `[ DONE ]`
Added 11 error-path tests: unclosed paren/list/dict, missing def/if/while body, ternary missing else, lambda fallback behavior, incomplete unpack at statement level. 172/172 tests pass.

### 3. `_parse_expr_or_assign` refactor — `[ DONE ]`
Extracted `_try_parse_self_attr_assign()` — Path 1 is now self-contained. Removed top-level `save`/reset and the redundant `self.pos = save` before Path 3. 173/173 tests pass.

---

## Medium Return

### 4. ParseError context enrichment — `[ DONE ]`
Added `expected: str | None` field to `ParseError`; `expect()` now populates it with the expected token type name. Tested via `test_parse_error_has_expected_field`.

### 5. Lexer dedent loop — `[ NOT AN ISSUE ]`
Complexity is O(depth) per dedent sequence (each pop is O(1)), not O(depth²) as CONCERNS.md stated. No fix needed.

### 6. Decorator support — `[ DONE ]`
Position-based disambiguation: `@expr` before `def`/`class` = decorator, elsewhere = self-attr.
Supports stacked, call-expression, and attribute decorators. Methods inside classes also supported.

---

## Gaps Found — `examples/showcase.lpp` (session 5)

Ran a non-trivial script exercising most Python paradigms. All working sections pass.
Gaps discovered, ranked by return:

### 7. `is` / `not in` — `[ DONE ]`
Added `IS` and `NOT` keywords to lexer; `_parse_comparison` handles `is`, `is not`, and `not in`. 8 new tests, 208/208 pass.

### 8. `**` (power) and `//` (floor div) — `[ DONE ]`
Added `STARSTAR`/`DOUBLESLASH` tokens; `_parse_power` inserted above multiplicative for correct precedence. 6 new tests, 214/214 pass.

### 9. List / dict comprehensions — `[ DONE ]`
Added `ListComp`/`DictComp` AST nodes; `_parse_comp_clauses` helper handles `for targets in iter (if cond)?`; iterable uses `_parse_pipeline` to avoid ternary conflict. 10 new tests, 224/224 pass.

### 10. Tuple literals / multi-value return — `[ DONE ]`
Added `Tuple` AST node; `_parse_stmt_tuple()` helper collects comma-separated exprs; used in return, assignment RHS, and expr statements. 7 new tests, 231/231 pass.

### 11. `*args` / `**kwargs` in function params — `[ DONE ]`
Added `kind` field to `Param`; `_parse_params` handles `STAR name` and `STARSTAR name`; transpiler emits `*`/`**` prefixes. 6 new tests, 237/237 pass.

### 12. Slice notation — `[ DONE ]`
Added `Slice` AST node; `_parse_subscript_key` handles `start:stop:step` with all optional parts. 10 new tests, 247/247 pass.

### 13. `assert` / `del` — `[ DONE ]`
Added `ASSERT`/`DEL` keywords, `AssertStatement`/`DelStatement` AST nodes, parser methods, and transpiler cases. 8 new tests, 255/255 pass.

### 14. `%=` (modulo-assign) — `[ DONE ]`
Added `PERCENTEQ` token to lexer MAP2 and both AUG dicts in parser. 2 new tests, 257/257 pass.

### 15. Set literals — `[ DONE ]`
Restructured `{...}` parser to peek for COLON (dict) vs COMMA/RBRACE (set); added `SetLiteral` AST node. 4 new tests, 261/261 pass.

### 16. `for/else` — `[ DONE ]`
Added `else_body` field to `ForStatement`; `_parse_for` checks for `ELSE` after body; transpiler emits `else:` block. 2 new tests, 263/263 pass.

### 17. Multiple inheritance — `[ DONE ]`
Changed `ClassDef.base: str | None` to `bases: list[str]`; parser collects comma-separated bases; transpiler joins them. 3 new tests, 266/266 pass.

---

## Gaps Found — static analysis (session 7)

### 18. `pass` in function body — `[ DONE ]`
Added `PASS` keyword and `PassStatement` AST node; `_parse_pass` dispatched from statement parser; transpiler emits `pass` directly (no implicit-return promotion). 3 new tests, 274/274 pass.

### 19. Multiple exception types per `except` clause — `[ DONE ]`
`_parse_try` now accepts `LPAREN ident, ident... RPAREN` for `exc_type`; `ErrHandler.exc_type` widened to `str | list[str] | None`; transpiler emits `(T1, T2)` when list. 2 new tests, 274/274 pass.

### 20. Set comprehensions — `[ DONE ]`
Added `SetComp` AST node; `_parse_primary` peeks for `FOR` after first `{`-expression (no colon); transpiler emits `{elt for targets in iter (if cond)?}`. 3 new tests, 274/274 pass.

### 21. Chained comparisons — `[ DONE ]`
Rewrote `_parse_comparison` as a collecting loop; yields `BinOp` for single op, `ChainedComparison(operands, ops)` for chains; transpiler interleaves. 5 new tests, 281/281 pass.

### 22. `while/else` — `[ DONE ]`
Added `else_body` field to `DoStatement`; `_parse_while` checks for `ELSE` after body; transpiler emits `else:` block. 2 new tests, 281/281 pass.

---

## Enterprise Packaging — Layer 1: Distribution & CLI

Plan: `docs/superpowers/plans/2026-04-18-enterprise-packaging.md`

### 23. PyPI metadata + `__version__` — `[ TODO ]`
Add description, authors, license, classifiers, and URLs to `pyproject.toml`. Expose `__version__` via `importlib.metadata` in `__init__.py`.

### 24. `--version` flag — `[ TODO ]`
`lpp --version` prints `lpp <version>`.

### 25. `--check` flag — `[ DONE ]`
Added `--check` argument to `cli.py`; short-circuits output after successful parse (`pass`). Existing error handler already exits 1 on `LexError`/`ParseError`. 3 new tests, 290/290 pass.

### 26. Directory compilation — `[ TODO ]`
`lpp src/ -o out/` compiles all `.lpp` files recursively, mirroring directory structure. Reports all errors, exits 1 if any file failed.

### 27. `watch` subcommand — `[ TODO ]`
`lpp watch <file|dir> -o <outdir>` polls for `mtime` changes every 500 ms and recompiles on save. Stdlib only, no new dependencies.

---

## Enterprise Packaging — Layer 2: DX (deferred)

- **Source maps** — thread line numbers through AST and transpiler so tracebacks point to `.lpp` lines. High value, touches every AST node.
- **Richer error output** — formatted errors with source snippet and caret (partially done in `cli.py`; full Rust-style context pending).
- **Watch mode** — covered in Layer 1.

## Enterprise Packaging — Layer 3: Type Annotations (deferred)

- **Type annotation syntax** — `x: int`, `def f(x: int) -> str:` require a design decision since `:` conflicts with class-base syntax. Candidate: `x::int`.

## Enterprise Packaging — Layer 4: Editor Tooling (deferred)

- **TextMate grammar** — syntax highlighting for VS Code / Sublime / GitHub.
- **LSP** — go-to-definition and inline errors.

---

## Low Priority / Deferred

- **String interpolation re-parsing** — O(n) per string, negligible in practice. Measure first.
- **Parser recursion depth** — only relevant for pathological input.
- **`yield` / generators** — `[ DONE ]` Added `YIELD` keyword, `YieldStatement(value, is_from)` AST node, `_parse_yield` (handles bare `yield`, `yield expr`, `yield from iter`); implicit-return suppressed. 5 new tests, 286/286 pass.
- **`async`/`await`** — Tier 6, deferred by design (changes `def` semantics, requires `async for`/`async with`).
- **Walrus operator `:=`** — niche; `n:=expr` conflicts with existing colon use.
