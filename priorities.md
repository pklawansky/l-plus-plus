# L++ Work Priorities

*Last updated: 2026-04-17 (session 5)*

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

### 7. `is` / `not in` — silent wrong output `[ HIGH ]`
- `x is None` → transpiles as `x, is, None` (comma-separated; `is` treated as name)
- `x not in col` → garbled output (`not` as name, `in` keyword left over)
- Fix: add `is` and `not in` as comparison operators in `_parse_comparison`

### 8. `**` (power) and `//` (floor div) — hard lex errors `[ HIGH ]`
- `a**b` → `ParseError: unexpected token STAR`
- `a//b` → `ParseError: unexpected token SLASH`
- Fix: add `STARSTAR` and `DOUBLESLASH` tokens to lexer + parser

### 9. List / dict comprehensions — `[ HIGH ]`
- `[x*x for x in r(n)]` → `ParseError: unexpected token FOR`
- `{k: v for ...}` → same
- Fix: detect `for` keyword inside `[...]`/`{...}` literals and parse as comprehension

### 10. Tuple literals / multi-value return — `[ HIGH ]`
- `return a, b` → `ParseError: unexpected token COMMA`
- `x = 1, 2, 3` → same
- Fix: add `Tuple` AST node; parse comma-separated expressions at statement boundaries

### 11. `*args` / `**kwargs` in function params — `[ MEDIUM ]`
- `def f *args **kwargs` → `ParseError: expected INDENT, got STAR`
- Fix: extend `_parse_params` to accept `*name` and `**name`

### 12. Slice notation — `[ MEDIUM ]`
- `lst[0:n]` → `ParseError: expected RBRACKET, got COLON`
- Fix: add `Slice` AST node; parse `start:stop` (and `start:stop:step`) inside `[...]`

### 13. `assert` / `del` — silent wrong output `[ MEDIUM ]`
- `assert x==1` → emits just `assert` (assertion silently dropped)
- `del x` → emits `del` then `x` as separate statements
- Fix: add `assert` and `del` as keywords and AST nodes

### 14. `%=` (modulo-assign) — hard parse error `[ MEDIUM ]`
- `x%=3` → `ParseError: unexpected token EQ`
- Fix: add `PERCENTEQ` token to lexer; handle in aug-assign parser

### 15. Set literals — `[ LOW ]`
- `{1, 2, 3}` → `ParseError: expected COLON, got COMMA`
- Fix: detect comma (no colon) inside `{...}` and parse as set

### 16. `for/else` — `[ LOW ]`
- `for i in r(3)\n  ...\nelse\n  ...` → `ParseError: unexpected token ELSE`
- Fix: check for `else` clause after `for` body in `_parse_statement`

### 17. Multiple inheritance — `[ LOW ]`
- `class Foo:Bar,Baz` → `ParseError: expected INDENT, got COMMA`
- Fix: parse comma-separated base list in `_parse_class`

---

## Low Priority / Deferred

- **String interpolation re-parsing** — O(n) per string, negligible in practice. Measure first.
- **Parser recursion depth** — only relevant for pathological input.
- **Type annotations** — Tier 4, deferred by design.
- **Generator/async support** — Tier 6, deferred by design.
- **Walrus operator `:=`** — niche; `n:=expr` conflicts with existing colon use.
