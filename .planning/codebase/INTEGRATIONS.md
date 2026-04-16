# External Integrations

**Analysis Date:** 2026-04-16

## APIs & External Services

**None detected**

This is a transpiler project with no external API integrations. The `l++` transpiler reads `.lpp` source files, parses them, and emits Python source code entirely through built-in Python stdlib.

## Data Storage

**Databases:**
- None - This is not applicable. The transpiler does not use any database system.

**File Storage:**
- Local filesystem only
  - Reading: Input `.lpp` files via CLI argument (`args.file`)
  - Writing: Python output to stdout or optional file via `-o` flag
  - Location: `src/lpp/cli.py` lines 35-36 (read) and 53-54 (write)

**Caching:**
- None - No caching layer implemented

## Authentication & Identity

**Auth Provider:**
- None - This is a local-only transpiler with no user authentication or identity management.

## Monitoring & Observability

**Error Tracking:**
- None - No integration with error tracking services

**Logs:**
- stderr output only
  - File not found errors: written to `sys.stderr`
  - Lexer/parser errors: formatted with line/column location and caret indicator
  - Location: `src/lpp/cli.py` function `_format_error()` (lines 8-21)
  - Internal errors: printed to stderr with exit code 1

## CI/CD & Deployment

**Hosting:**
- PyPI (intended distribution target based on setuptools `pyproject.toml` configuration)
- No hosting platform configured

**CI Pipeline:**
- None detected - No `.github/workflows`, `.gitlab-ci.yml`, `.circleci/config.yml`, or similar

## Environment Configuration

**Required env vars:**
- None - No environment variables are required for operation

**Configuration approach:**
- Command-line arguments only
  - `file`: Input `.lpp` source file (required)
  - `-o, --output`: Optional output file path
  - `--run`: Flag to execute transpiled Python immediately

**Secrets location:**
- Not applicable - No secrets or credentials needed

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Runtime Execution

**Code Execution:**
- The transpiler can execute compiled Python code directly via `exec()` when `--run` flag is used
- Location: `src/lpp/cli.py` line 51
- Security: Code execution uses a clean namespace with `{"__name__": "__main__"}` to simulate script execution

---

*Integration audit: 2026-04-16*
