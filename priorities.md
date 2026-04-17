# L++ Work Priorities

*Last updated: 2026-04-17 (session 2)*

---

## Highest Return

### 1. String escape handling — `[ DONE ]`
`_escape_str_content` implemented in `transpiler.py:234-251`, `_string()` uses it on all paths. 7 transpiler tests passing. Was already complete before this session.

### 2. Parser error coverage — `[ DONE ]`
Added 11 error-path tests: unclosed paren/list/dict, missing def/if/while body, ternary missing else, lambda fallback behavior, incomplete unpack at statement level. 172/172 tests pass.

### 3. `_parse_expr_or_assign` refactor — `[ PENDING ]`
**Why:** `parser.py:574-662` has three mutually exclusive paths with manual save/restore. Highest-friction area for adding new assignment forms.
**Done when:** Cleaner dispatch; all existing assignment tests pass; `@x+=1`, `d[k],a=...` edge cases covered.

---

## Medium Return

### 4. ParseError context enrichment — `[ PENDING ]`
**Why:** Currently just line + col. An "expected" field would make error messages much more useful.
**Files:** `src/lpp/parser.py:6-10`

### 5. Lexer dedent loop — `[ NOT AN ISSUE ]`
Complexity is O(depth) per dedent sequence (each pop is O(1)), not O(depth²) as CONCERNS.md stated. No fix needed.

---

## Low Priority / Deferred

- **String interpolation re-parsing** — O(n) per string, negligible in practice. Measure first.
- **Parser recursion depth** — only relevant for pathological input.
- **Type annotations** — Tier 4, deferred by design.
- **Decorators** — conflicts with `@` self-attr syntax, needs design work.
- **Generator/async support** — Tier 6, deferred by design.
