# L++ Work Priorities

*Last updated: 2026-04-17 (session 4)*

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

## Low Priority / Deferred

- **String interpolation re-parsing** — O(n) per string, negligible in practice. Measure first.
- **Parser recursion depth** — only relevant for pathological input.
- **Type annotations** — Tier 4, deferred by design.
- **Decorators** — `[ DONE ]` See item 6 above.
- **Generator/async support** — Tier 6, deferred by design.
