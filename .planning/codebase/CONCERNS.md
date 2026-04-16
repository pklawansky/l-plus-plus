# Codebase Concerns

**Analysis Date:** 2026-04-16

## Tech Debt

**Parser size and complexity:**
- Issue: `src/lpp/parser.py` is 662 lines with deeply nested recursive descent methods and multiple lookahead/backtracking patterns
- Files: `src/lpp/parser.py` (lines 103-121 lambda lookahead, 574-662 unpacking lookahead)
- Impact: Difficult to debug parsing ambiguities; error recovery is limited; adding new statements requires edits in multiple parser methods
- Fix approach: Consider extracting expression parsing into separate expression parser class; refactor `_parse_expr_or_assign` to use clearer state machine or explicit attempt sequence

**String escape handling complexity:**
- Issue: Escape sequence unescaping happens in lexer (`src/lpp/lexer.py` line 125), but semantic characters must be re-escaped in transpiler (`src/lpp/transpiler.py` lines 235-251)
- Files: `src/lpp/lexer.py` (line 125), `src/lpp/transpiler.py` (lines 221-251)
- Impact: Risk of mismatched escape sequences; documented as "Tier 1" fix in `/docs/superpowers/specs/2026-04-16-tier1-string-escaping-design.md`
- Fix approach: Already designed and pending implementation per Tier 1 spec (escape-str-content method exists but needs full rollout to all string paths)

**Limited error context in ParseError:**
- Issue: `ParseError` stores only line and col; no context about what was expected or what token triggered the error
- Files: `src/lpp/parser.py` (lines 6-10)
- Impact: User sees raw "expected X, got Y" messages without parse state context; hard to diagnose why a valid expression failed
- Fix approach: Enhance error class with optional context field; provide better hints in exception messages

## Known Bugs

**None explicitly marked as bugs.**

The string escape issue (documented in Tier 1 spec) is a known limitation, not a hidden bug. All integration tests currently pass.

## Security Considerations

**Code execution via `--run` flag:**
- Risk: `src/lpp/cli.py` line 51 uses `exec(compile(python_src, args.file, "exec"), {"__name__": "__main__"})` to execute user code with restricted globals, but any transpiled L++ code can still call arbitrary Python functions
- Files: `src/lpp/cli.py` (lines 50-51)
- Current mitigation: Restricted globals dict prevents access to `__builtins__` but prelude injects all builtins (`print`, `len`, `range`, etc.) deliberately
- Recommendations: 
  - Document that `lpp --run` is unsafe for untrusted input (should only run code you wrote)
  - Consider warning message when `--run` is used
  - For sandboxed execution, document use of external tools like `docker`, `nix`, or `sandbox` instead

**Prelude alias injection:**
- Risk: `src/lpp/prelude.py` lines 46-51 injects 43 aliases into user code without warning; conflicts with user variable names are silent
- Files: `src/lpp/prelude.py` (lines 46-51)
- Current mitigation: None; aliases are intentionally exposed
- Recommendations: Document in README that prelude names (`p`, `l`, `r`, `s`, `i`, `f`, `b`, `t`, `li`, `di`, `se`, `tu`, `en`, `zi`, `ma`, `fi`, `so`, `rv`, `su`, `mn`, `mx`, `ab`, `ro`, `an`, `al`, `nx`, `ip`, `op`, `rp`, `ga`, `sa`, `ha`, `od`, `ch`, `pw`, `hx`, `isa`, `sc`) are reserved and should not be redefined

## Performance Bottlenecks

**String interpolation re-parsing:**
- Problem: Every `$expr$` inside a string triggers full lexer + parser calls (`src/lpp/parser.py` lines 67-68)
- Files: `src/lpp/parser.py` (lines 46-76 `_parse_string_literal`)
- Cause: Nested lexer/parser creation; no caching; O(n) for n interpolations per string
- Improvement path: 
  - For typical strings (simple identifiers/literals), avoid full parser; inline expression parser for common cases
  - Cache tokenizer results if repeated interpolations detected
  - Measure impact first; may be negligible for typical code

**Lexer indentation stack management:**
- Problem: Every dedent triggers a loop (`src/lpp/lexer.py` lines 68-70) with list pops; large dedent sequences (nested blocks closing) are O(depth²)
- Files: `src/lpp/lexer.py` (lines 62-75)
- Cause: No optimization for multi-level dedents
- Improvement path: 
  - Minor: accept current approach (typical code has shallow nesting)
  - Better: optimize multi-dedent case with single pop+range instead of loop

## Fragile Areas

**Parser lookahead patterns:**
- Files: `src/lpp/parser.py` (lines 103-121 lambda, lines 574-662 unpacking)
- Why fragile: Both use manual position save/restore with try/except; if lookahead changes, must update save/restore locations; easy to introduce off-by-one bugs
- Safe modification: When changing lambda or unpacking parsing, test all error cases (e.g., `x->`, incomplete unpack). Add dedicated test suite for parse failure modes
- Test coverage: `tests/test_parser.py` has happy-path tests but minimal error/edge case coverage for lookahead

**String literal handling:**
- Files: `src/lpp/parser.py` (lines 48-76), `src/lpp/lexer.py` (lines 117-134)
- Why fragile: Escape sequence handling spans lexer (unescape) + transpiler (re-escape); mismatch causes silent output errors
- Safe modification: Any change to escape handling must test full lex→parse→transpile→exec pipeline (see integration test `test_string_escape_roundtrip`)
- Test coverage: `tests/test_integration.py` line 61-64 covers roundtrip; `tests/test_transpiler.py` needs more escape sequence tests

**Assignment target parsing:**
- Files: `src/lpp/parser.py` (lines 574-662 `_parse_expr_or_assign` with three paths)
- Why fragile: Three separate paths (self-attr, unpacking, general expression) with mutual exclusion logic; adding new assignment forms requires refactoring all three
- Safe modification: Refactor to clearer dispatch; test `a=1`, `@x=1`, `a,b=1,2`, `d[k]=1`, `obj.attr=1` in all combinations with aug-assignment
- Test coverage: Basic cases exist; edge cases (e.g., `@x+=1`, `d[k],a=...`) need tests

## Scaling Limits

**Parser recursion depth:**
- Current capacity: Typical Python files have nesting up to 5-10 levels; parser uses recursive descent
- Limit: No explicit limit; Python's recursion limit (usually 1000) is shared with entire transpiler
- Scaling path: 
  - For deeply nested expressions/blocks (pathological cases), parser will hit recursion limit
  - Not a practical concern for normal code; document if encountered
  - If needed: convert recursive descent to iterative parser with explicit stack

**Prelude size:**
- Current: 43 aliases injected at top of every file
- Limit: Each alias adds 1-2 lines of Python; 43 * 2 = 86 lines overhead per transpiled file
- Scaling path: Acceptable; prelude is fixed size, not input-dependent

## Dependencies at Risk

**No external package dependencies:**
- The transpiler uses only Python stdlib (dataclasses, enum, typing)
- No risk of breaking version updates or abandoned packages

**TokenType and KEYWORDS mismatch:**
- Risk: If a keyword is added to `KEYWORDS` dict but `TokenType` enum is not updated, lexer will fail silently
- Impact: New keyword won't be recognized; no type safety enforcement
- Migration plan: Use tools/validate_tokens.py before committing new keywords; tests should validate all keywords are in both places

## Missing Critical Features

**Type annotations:**
- Problem: L++ has no type annotation support; deferred to Tier 4
- Blocks: Writing type-hinted Python code requires workarounds or falling back to Python
- Status: Documented as "Tier 4" future work; acceptable for MVP

**Decorators:**
- Problem: `@` is used for method/self-attribute syntax; decorator syntax conflicts
- Blocks: Cannot express Python decorators without design change
- Status: Documented as deferred; low priority for LLM token-minimization use case

**Generator/async support:**
- Problem: No `yield`, `async`, `await` keywords
- Blocks: Writing async code or generators requires Python output
- Status: Documented as "Tier 6"; acceptable for MVP

## Test Coverage Gaps

**Parser error cases:**
- What's not tested: ParseError conditions (malformed syntax, missing tokens)
- Files: `src/lpp/parser.py` (error paths throughout)
- Risk: A refactor could introduce silent parse failures or wrong error messages
- Priority: Medium — add error path tests to `tests/test_parser.py`
- Example gaps:
  - Missing closing paren in function call: `add(1,2` → ParseError
  - Lambda without arrow: `x->` → ParseError
  - Incomplete unpack: `a,b` (no `=`) → should be treated as expression, not error

**Lexer error cases:**
- What's not tested: LexError edge cases (malformed strings, invalid operators)
- Files: `src/lpp/lexer.py` (error paths)
- Risk: A change to operator scanning could silently accept invalid operators
- Priority: Medium — add error path tests to `tests/test_lexer.py`
- Example gaps:
  - Unterminated strings: `"hello` → LexError
  - Invalid escape sequences: `"\q"` → should either error or be preserved
  - Operator ambiguity: `<<` vs `<` followed by `<` (currently correctly handled, but no explicit test)

**Transpiler edge cases:**
- What's not tested: Transpiler handling of unusual AST nodes
- Files: `src/lpp/transpiler.py` (match cases)
- Risk: If parser generates unexpected AST structures, transpiler match falls through to NotImplementedError
- Priority: Low — parser validation is better defense, but consider test coverage for:
  - Empty blocks: `def f\n  pass` → empty function
  - Nested pipeline: `x | f | g | h` → complex expression
  - Mixed assignments: `@x,y = ...` (self-attr unpacking) → not currently supported, should error in parser, not transpiler

---

*Concerns audit: 2026-04-16*
