# L++ Work Priorities

*Last updated: 2026-04-17*

---

## Highest Return

### 1. String escape handling — `[ IN PROGRESS ]`
**Why:** Unescape-in-lexer / re-escape-in-transpiler split is the biggest silent correctness risk. Spec already exists at `docs/superpowers/specs/2026-04-16-tier1-string-escaping-design.md`.
**Files:** `src/lpp/lexer.py:125`, `src/lpp/transpiler.py:221-251`
**Done when:** All string paths route through `escape_str_content`; integration test `test_string_escape_roundtrip` passes; no escape sequence mismatch possible.

### 2. Parser error coverage — `[ PENDING ]`
**Why:** `test_parser.py` has happy-path only. Lookahead patterns (`parser.py:103-121`, `574-662`) are fragile — a refactor could introduce silent failures.
**Work:** Add ~10-15 error-path tests covering: missing closing paren, `x->` (lambda no body), incomplete unpack, unterminated string, invalid escape.
**Done when:** All ParseError/LexError paths have at least one test.

### 3. `_parse_expr_or_assign` refactor — `[ PENDING ]`
**Why:** `parser.py:574-662` has three mutually exclusive paths with manual save/restore. Highest-friction area for adding new assignment forms.
**Done when:** Cleaner dispatch; all existing assignment tests pass; `@x+=1`, `d[k],a=...` edge cases covered.

---

## Medium Return

### 4. ParseError context enrichment — `[ PENDING ]`
**Why:** Currently just line + col. An "expected" field would make error messages much more useful.
**Files:** `src/lpp/parser.py:6-10`

### 5. Lexer dedent loop — `[ PENDING ]`
**Why:** O(depth²) for large dedents. Trivial one-liner fix.
**Files:** `src/lpp/lexer.py:68-70`
**Fix:** Replace pop loop with single slice.

---

## Low Priority / Deferred

- **String interpolation re-parsing** — O(n) per string, negligible in practice. Measure first.
- **Parser recursion depth** — only relevant for pathological input.
- **Type annotations** — Tier 4, deferred by design.
- **Decorators** — conflicts with `@` self-attr syntax, needs design work.
- **Generator/async support** — Tier 6, deferred by design.
