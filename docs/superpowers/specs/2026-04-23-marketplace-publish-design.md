# Marketplace & PyPI Publish — Design Spec

**Date:** 2026-04-23  
**Status:** Approved

---

## Overview

Publish the `lpp` Python package to PyPI and the L++ VS Code extension to the Marketplace. Both are manual one-time operations. Account creation steps are documented as prerequisites in the implementation plan.

---

## Scope

Two sequential publishes:

1. **PyPI** — makes `pip install lpp` work for end users
2. **VS Code Marketplace** — makes the extension installable from within VS Code

---

## PyPI Publish

`pyproject.toml` already has all required metadata (name, version, description, authors, license, classifiers, URLs). No code changes required.

**Tooling:** `build` + `twine`

```bash
python -m build          # produces dist/lpp-0.2.0.tar.gz and dist/lpp-0.2.0-py3-none-any.whl
twine upload dist/*      # uploads with PyPI API token
```

**Prerequisites (manual, documented in plan):**
- Create account at pypi.org
- Verify email
- Generate API token (scope: entire account for first publish)
- Configure `~/.pypirc` or pass token via `TWINE_PASSWORD` env var

---

## VS Code Extension Changes

### `package.json`

Add required Marketplace fields:

```json
{
  "publisher": "pklawansky",
  "description": "Syntax highlighting and language server for the L++ language",
  "categories": ["Programming Languages"],
  "keywords": ["lpp", "l++", "transpiler"],
  "repository": {
    "type": "git",
    "url": "https://github.com/pklawansky/l-plus-plus"
  },
  "license": "MIT"
}
```

Add devDependency and scripts:

```json
{
  "devDependencies": {
    "@vscode/vsce": "^3.0.0"
  },
  "scripts": {
    "package": "vsce package",
    "publish": "vsce publish"
  }
}
```

### `README.md` (repo root — used as Marketplace listing page)

Add a **Prerequisites** section near the top:

```markdown
## Prerequisites

The syntax highlighting works with no setup. For diagnostics, hover, go-to-definition,
and completions, install the L++ compiler:

pip install lpp
```

### `.vscodeignore`

Exclude everything not needed in the packaged `.vsix`:

```
src/
tests/
docs/
examples/
dist/
.github/
.claude/
**/__pycache__/
**/*.py
**/*.pyc
node_modules/.cache/
```

### `CHANGELOG.md`

Single initial entry:

```markdown
# Changelog

## [0.2.0]

- Syntax highlighting for `.lpp` files (keywords, strings, comments, operators, self-attrs, built-ins)
- LSP diagnostics: syntax errors and undefined variable detection
- Hover documentation for built-ins and user-defined symbols
- Go-to-definition for functions, classes, and variables
- Completions: keywords, built-ins, and workspace symbols
```

### Publish Command

```bash
vsce publish
```

**Prerequisites (manual, documented in plan):**
- Create Microsoft account (pklawansky@gmail.com)
- Create publisher `pklawansky` at https://marketplace.visualstudio.com/manage/createpublisher
- Generate Azure DevOps PAT (scope: Marketplace → Manage)
- Authenticate: `vsce login pklawansky`

---

## Sequencing

1. Complete PyPI account setup → publish `lpp` to PyPI
2. Verify `pip install lpp` works
3. Complete VS Code publisher setup → publish extension
4. Verify extension appears on Marketplace and installs cleanly

---

## Out of Scope

- Automated publish via GitHub Actions (can be added later)
- Extension icon (can be added in a future version)
- `async`/`await` or other language features
