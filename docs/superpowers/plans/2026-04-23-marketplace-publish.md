# Marketplace & PyPI Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the `lpp` Python package to PyPI and the L++ VS Code extension to the Marketplace so users can `pip install lpp` and install the extension directly from VS Code.

**Architecture:** Two sequential one-time publish operations. PyPI first (so the Marketplace README's install instruction is accurate), then the VS Code extension. All code changes are configuration/metadata — no Python source changes needed. Manual account-creation prerequisites are documented per task.

**Tech Stack:** Python `build` + `twine` (PyPI), `@vscode/vsce` (VS Code Marketplace), `npm`

---

## Files

| File | Action | Purpose |
|------|--------|---------|
| `package.json` | Modify | Add publisher, description, categories, keywords, repository, license, vsce devDependency and scripts |
| `README.md` | Modify | Add VS Code Prerequisites section so the Marketplace listing explains the `pip install lpp` requirement |
| `.vscodeignore` | Create | Exclude Python source, tests, docs, dist from the packaged `.vsix` |
| `CHANGELOG.md` | Create | Required by vsce; single 0.2.0 entry listing all features |

---

## Task 1: Publish `lpp` to PyPI

> **Manual prerequisites** — complete these before running any commands:
>
> 1. Go to https://pypi.org/account/register/ and create an account using pklawansky@gmail.com
> 2. Verify your email address
> 3. Enable two-factor authentication (PyPI requires this for publishing)
> 4. Go to https://pypi.org/manage/account/token/ → **Add API token**
>    - Token name: `lpp-publish`
>    - Scope: **Entire account** (for first upload; can scope to project after)
> 5. Copy the token (starts with `pypi-`) — you only see it once
> 6. Set it as an environment variable so twine can use it:
>    ```powershell
>    $env:TWINE_USERNAME = "__token__"
>    $env:TWINE_PASSWORD = "pypi-YOUR_TOKEN_HERE"
>    ```

**Files:** None (no code changes — pyproject.toml already has all metadata)

- [ ] **Step 1: Install build tools**

```powershell
pip install build twine
```

Expected: both install without errors.

- [ ] **Step 2: Build the distribution**

```powershell
python -m build
```

Expected output (last few lines):
```
Successfully built lpp-0.2.0.tar.gz and lpp-0.2.0-py3-none-any.whl
```

Verify `dist/` contains exactly two files:
```powershell
ls dist/
```
Expected:
```
lpp-0.2.0-py3-none-any.whl
lpp-0.2.0.tar.gz
```

- [ ] **Step 3: Check the distribution**

```powershell
twine check dist/*
```

Expected: `PASSED` for both files. If any warnings appear, fix them in `pyproject.toml` before continuing.

- [ ] **Step 4: Upload to PyPI**

```powershell
twine upload dist/*
```

Expected output:
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading lpp-0.2.0-py3-none-any.whl
Uploading lpp-0.2.0.tar.gz
View at: https://pypi.org/project/lpp/0.2.0/
```

- [ ] **Step 5: Verify installation works**

Create a temporary venv and install from PyPI:

```powershell
python -m venv /tmp/lpp-verify
/tmp/lpp-verify/Scripts/activate
pip install lpp
lpp --version
deactivate
```

Expected: `lpp 0.2.0`

---

## Task 2: Update `package.json` with Marketplace metadata

**Files:**
- Modify: `package.json`

- [ ] **Step 1: Verify current package.json state**

```powershell
cat package.json
```

Confirm it currently has no `publisher`, `description`, `categories`, `keywords`, `repository`, or `license` fields.

- [ ] **Step 2: Replace package.json with full metadata**

Replace the entire contents of `package.json` with:

```json
{
  "name": "lpp-syntax",
  "displayName": "L++ Syntax",
  "description": "Syntax highlighting and language server for the L++ language",
  "version": "0.2.0",
  "publisher": "pklawansky",
  "license": "MIT",
  "engines": { "vscode": "^1.82.0" },
  "categories": ["Programming Languages"],
  "keywords": ["lpp", "l++", "transpiler", "python"],
  "repository": {
    "type": "git",
    "url": "https://github.com/pklawansky/l-plus-plus"
  },
  "main": "client/extension.js",
  "activationEvents": ["onLanguage:lpp"],
  "dependencies": {
    "vscode-languageclient": "^9.0.0"
  },
  "devDependencies": {
    "@vscode/vsce": "^3.0.0"
  },
  "scripts": {
    "package": "vsce package",
    "publish": "vsce publish"
  },
  "contributes": {
    "languages": [{ "id": "lpp", "extensions": [".lpp"] }],
    "grammars": [{
      "language": "lpp",
      "scopeName": "source.lpp",
      "path": "./syntaxes/lpp.tmLanguage.json"
    }]
  }
}
```

- [ ] **Step 3: Install devDependency**

```powershell
npm install
```

Expected: `added 1 package` (or similar — installs `@vscode/vsce`).

- [ ] **Step 4: Verify vsce is available**

```powershell
npx vsce --version
```

Expected: a version string like `3.x.x`.

- [ ] **Step 5: Commit**

```powershell
git add package.json package-lock.json
git commit -m "chore(extension): add Marketplace metadata and vsce tooling"
```

---

## Task 3: Create `.vscodeignore`

**Files:**
- Create: `.vscodeignore`

- [ ] **Step 1: Check what vsce would include without a .vscodeignore**

```powershell
npx vsce ls
```

This lists every file that would be packaged. Note that `src/`, `tests/`, `docs/`, `dist/`, etc. are all included — we need to exclude them.

- [ ] **Step 2: Create `.vscodeignore`**

Create `.vscodeignore` at the repo root with these contents:

```
src/
tests/
docs/
examples/
dist/
.github/
.claude/
.planning/
.worktrees/
tools/
**/__pycache__/
**/*.py
**/*.pyc
pyproject.toml
CLAUDE.md
priorities.md
.gitignore
```

- [ ] **Step 3: Verify the package contents are clean**

```powershell
npx vsce ls
```

Expected output should only contain:
```
client/extension.js
syntaxes/lpp.tmLanguage.json
package.json
README.md
node_modules/vscode-languageclient/...  (and its transitive deps)
```

(`CHANGELOG.md` is not here yet — it's added in Task 4.)

No `src/`, `tests/`, `docs/`, `examples/`, or `*.py` files should appear.

- [ ] **Step 4: Commit**

```powershell
git add .vscodeignore
git commit -m "chore(extension): add .vscodeignore to exclude non-extension files"
```

---

## Task 4: Create `CHANGELOG.md`

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Create CHANGELOG.md**

Create `CHANGELOG.md` at the repo root with these contents:

```markdown
# Changelog

## [0.2.0] — 2026-04-23

### Added

- Syntax highlighting for `.lpp` files: keywords, strings with `$...$` interpolation,
  comments, numbers, constants (`None`, `True`, `False`), storage keywords (`def`, `class`),
  control flow, self-attrs (`@x`), and built-in aliases (`p`, `l`, `r`, etc.)
- Language server — requires `pip install lpp` (syntax highlighting works without it):
  - Diagnostics: syntax errors and undefined variable detection
  - Hover: documentation for built-in aliases and user-defined symbols
  - Go-to-definition: functions, classes, and variables
  - Completions: keywords, built-in aliases, and workspace symbols
```

- [ ] **Step 2: Verify vsce package succeeds**

```powershell
npm run package
```

Expected: produces `lpp-syntax-0.2.0.vsix` with no errors. A warning about a missing icon is fine — ignore it.

- [ ] **Step 3: Commit**

```powershell
git add CHANGELOG.md
git commit -m "chore(extension): add CHANGELOG for Marketplace listing"
```

---

## Task 5: Add VS Code prerequisites section to `README.md`

**Files:**
- Modify: `README.md`

The README doubles as the Marketplace listing page. It needs a section near the top explaining the `pip install lpp` prerequisite for LSP features.

- [ ] **Step 1: Add VS Code Extension section to README.md**

Insert the following block immediately after the opening paragraph (after the line ending `...while keeping the code fully executable.`) and before the `---` divider:

```markdown

---

## VS Code Extension

Install the **L++ Syntax** extension from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=pklawansky.lpp-syntax) for syntax highlighting, diagnostics, hover, and completions.

**Prerequisites for language server features:**

```sh
pip install lpp
```

Syntax highlighting works without the compiler installed. Diagnostics, hover,
go-to-definition, and completions require `lpp` to be on your `PATH`.
```

- [ ] **Step 2: Verify README renders correctly**

Open `README.md` in a Markdown preview (VS Code: `Ctrl+Shift+V`) and confirm:
- The new section appears near the top
- The code block renders correctly
- No broken formatting

- [ ] **Step 3: Commit**

```powershell
git add README.md
git commit -m "docs: add VS Code extension prerequisites section to README"
```

---

## Task 6: Publish VS Code Extension to Marketplace

> **Manual prerequisites** — complete these before running any commands:
>
> 1. Sign in to https://marketplace.visualstudio.com/manage with your Microsoft account (pklawansky@gmail.com)
> 2. Click **Create publisher**:
>    - Publisher ID: `pklawansky`
>    - Display name: `Phillip Klawansky`
>    - Leave other fields blank or fill as desired
> 3. Go to https://dev.azure.com/ → sign in → click your profile (top right) → **Personal access tokens**
> 4. Click **+ New Token**:
>    - Name: `vsce`
>    - Organization: **All accessible organizations**
>    - Expiration: 1 year
>    - Scopes: **Custom defined** → check **Marketplace > Manage**
> 5. Copy the PAT — you only see it once

**Files:** None (all config changes already committed in Tasks 2–5)

- [ ] **Step 1: Authenticate vsce with your publisher account**

```powershell
npx vsce login pklawansky
```

When prompted for PAT, paste the token from the prerequisites above.

Expected: `The Personal Access Token verification succeeded for the publisher 'pklawansky'.`

- [ ] **Step 2: Do a final dry-run package**

```powershell
npm run package
```

Expected: `lpp-syntax-0.2.0.vsix` produced with no errors.

Inspect the .vsix contents one more time:

```powershell
npx vsce ls
```

Confirm no Python source files or test files are included.

- [ ] **Step 3: Publish**

```powershell
npm run publish
```

Expected output:
```
Publishing pklawansky.lpp-syntax@0.2.0...
Extension URL: https://marketplace.visualstudio.com/items?itemName=pklawansky.lpp-syntax
```

- [ ] **Step 4: Verify on Marketplace**

Wait 2–5 minutes for propagation, then:

1. Open https://marketplace.visualstudio.com/items?itemName=pklawansky.lpp-syntax — confirm the listing appears
2. In VS Code: open Extensions panel → search `l++ syntax` → confirm it appears and can be installed

- [ ] **Step 5: Commit priorities update**

```powershell
git add priorities.md
git commit -m "chore(priorities): mark Marketplace and PyPI publish as DONE"
```

---

## Rollback Notes

- **PyPI:** A published release cannot be deleted (only yanked). If something is wrong with 0.2.0, fix it and publish 0.2.1.
- **VS Code Marketplace:** A published extension can be unpublished from the Marketplace management page. The extension ID `pklawansky.lpp-syntax` is permanent once used.
