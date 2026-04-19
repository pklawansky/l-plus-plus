# TextMate Grammar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `syntaxes/lpp.tmLanguage.json` — a TextMate grammar that highlights L++ source files in VS Code, Sublime Text, and GitHub.

**Architecture:** Single JSON file using TextMate grammar format (Oniguruma regex, `repository`-based rule reuse). Ten token categories (comments, strings with `$...$` interpolation, numbers, language constants, two keyword tiers, self-attributes, built-in functions, operators) implemented as named repository rules referenced from the top-level `patterns` array.

**Tech Stack:** TextMate grammar JSON (Oniguruma regex), verified parseable with Python `json` module.

---

## File Map

| Action | Path |
|---|---|
| Create | `syntaxes/lpp.tmLanguage.json` |

---

### Task 1: Create the TextMate grammar file

**Files:**
- Create: `syntaxes/lpp.tmLanguage.json`

- [ ] **Step 1: Create the `syntaxes/` directory and write the grammar file**

Create `syntaxes/lpp.tmLanguage.json` with this exact content:

```json
{
  "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
  "name": "L++",
  "scopeName": "source.lpp",
  "fileTypes": ["lpp"],
  "patterns": [
    { "include": "#comment" },
    { "include": "#string" },
    { "include": "#number" },
    { "include": "#constant" },
    { "include": "#storage" },
    { "include": "#control" },
    { "include": "#keyword" },
    { "include": "#self-attr" },
    { "include": "#builtin" },
    { "include": "#operator" }
  ],
  "repository": {
    "comment": {
      "match": "#[^\\n]*",
      "name": "comment.line.number-sign.lpp"
    },
    "string": {
      "name": "string.quoted.double.lpp",
      "begin": "\"",
      "end": "\"",
      "patterns": [
        { "include": "#escape" },
        { "include": "#interpolation" }
      ]
    },
    "escape": {
      "match": "\\\\[nt\"\\\\]",
      "name": "constant.character.escape.lpp"
    },
    "interpolation": {
      "name": "meta.interpolation.lpp",
      "begin": "\\$",
      "end": "\\$",
      "beginCaptures": {
        "0": { "name": "punctuation.definition.template-expression.begin.lpp" }
      },
      "endCaptures": {
        "0": { "name": "punctuation.definition.template-expression.end.lpp" }
      },
      "patterns": [
        { "include": "$self" }
      ]
    },
    "number": {
      "match": "\\b\\d+(\\.\\d+)?\\b",
      "name": "constant.numeric.lpp"
    },
    "constant": {
      "match": "\\b(None|True|False)\\b",
      "name": "constant.language.lpp"
    },
    "storage": {
      "match": "\\b(def|class)\\b",
      "name": "storage.type.lpp"
    },
    "control": {
      "match": "\\b(if|elif|else|for|in|while|return|break|continue|try|except|finally|raise|with|yield)\\b",
      "name": "keyword.control.lpp"
    },
    "keyword": {
      "match": "\\b(use|alias|as|from|global|nl|is|not|assert|del|pass)\\b",
      "name": "keyword.other.lpp"
    },
    "self-attr": {
      "match": "@[A-Za-z_]\\w*",
      "name": "variable.other.readwrite.instance.lpp"
    },
    "builtin": {
      "match": "\\b(p|l|r|s|i|f|b|t|li|di|se|tu|en|zi|ma|fi|so|rv|su|mn|mx|ab|ro|an|al|nx|ip|op|rp|ga|sa|ha|od|ch|pw|hx|isa|sc)\\b(?=\\s*[(!])",
      "name": "support.function.builtin.lpp"
    },
    "operator": {
      "match": "(->|<<|[|&!])",
      "name": "keyword.operator.lpp"
    }
  }
}
```

- [ ] **Step 2: Validate JSON is parseable**

Run from the repo root:

```
python -c "import json; json.load(open('syntaxes/lpp.tmLanguage.json')); print('JSON valid')"
```

Expected output:
```
JSON valid
```

If it prints a `json.JSONDecodeError`, the file has a syntax error — fix it before continuing.

- [ ] **Step 3: Commit**

```bash
git add syntaxes/lpp.tmLanguage.json
git commit -m "feat(editor): add TextMate grammar for L++ syntax highlighting"
```

---

### Task 2: Manual verification in VS Code

This task cannot be automated — it requires a human with VS Code installed.

**Files:** None changed — this is a verification-only task.

- [ ] **Step 4: Associate `.lpp` with the grammar in VS Code**

Add this to your VS Code `settings.json` (open via `Ctrl+Shift+P` → "Open User Settings JSON"):

```json
"files.associations": {
  "*.lpp": "source.lpp"
}
```

Then open `examples/showcase.lpp` in VS Code. If the grammar is not auto-detected (no `package.json` manifest), install the [vscode-textmate-test](https://marketplace.visualstudio.com/items?itemName=KoalaSoft.vscode-textmate-test) extension or test by adding a minimal `package.json` (see note below).

**Simpler path:** Open the repo folder in VS Code, then use `Ctrl+Shift+P` → "Change Language Mode" → "Configure File Association for '.lpp'" and select "L++" if it appears, or manually point to the grammar.

**Quickest path for local testing:** Install the [TextMate Grammar Viewer](https://marketplace.visualstudio.com/items?itemName=Togusa09.tmlanguage) extension and open `syntaxes/lpp.tmLanguage.json` directly.

- [ ] **Step 5: Verify each token category using "Inspect Editor Tokens and Scopes"**

With `examples/showcase.lpp` open, press `Ctrl+Shift+P` → "Developer: Inspect Editor Tokens and Scopes". Place the cursor on each of the following and confirm the listed scope appears:

| Token | Expected scope |
|---|---|
| `# showcase.lpp` (line 1) | `comment.line.number-sign.lpp` |
| `"Vec2($@x$, $@y$)"` (line 28 — full string) | `string.quoted.double.lpp` |
| `$` delimiters in `$@x$` | `punctuation.definition.template-expression.begin/end.lpp` |
| `@x` inside `$@x$` | `variable.other.readwrite.instance.lpp` |
| `\\n` in an escape sequence | `constant.character.escape.lpp` |
| `0.5` (line 19) | `constant.numeric.lpp` |
| `None` (line 133) | `constant.language.lpp` |
| `def` (line 12) | `storage.type.lpp` |
| `class` (line 11) | `storage.type.lpp` |
| `if` (line 89) | `keyword.control.lpp` |
| `return` (line 69) | `keyword.control.lpp` |
| `use` (line 4) | `keyword.other.lpp` |
| `alias` (line 173) | `keyword.other.lpp` |
| `@x` (line 13) | `variable.other.readwrite.instance.lpp` |
| `@property` (line 16) | `variable.other.readwrite.instance.lpp` |
| `p(` (line 215) — the `p` | `support.function.builtin.lpp` |
| `li!` (line 125) — the `li` | `support.function.builtin.lpp` |
| `i = 5` — the `i` | NOT `support.function.builtin.lpp` (should be plain identifier) |
| `->` (line 35) | `keyword.operator.lpp` |
| `\|` (line 35) | `keyword.operator.lpp` |
| `!` (line 35) | `keyword.operator.lpp` |
| `&` (line 175) | `keyword.operator.lpp` |
| `<<` (line 77) | `keyword.operator.lpp` |

- [ ] **Step 6: Commit verification result**

If all checks pass, update `priorities.md` to mark TextMate grammar as DONE with a one-line summary, then commit:

```bash
git add priorities.md
git commit -m "chore(priorities): mark TextMate grammar DONE"
```

---

## Notes for VS Code Extension Wrapping (Future Work)

To make the grammar auto-detected by VS Code without manual file association, a minimal `package.json` is needed. This is deferred (Layer 4 of Enterprise Packaging). The grammar file itself requires zero changes — only the manifest needs to be added.

Minimal future `package.json`:
```json
{
  "name": "lpp-syntax",
  "displayName": "L++ Syntax",
  "version": "0.1.0",
  "engines": { "vscode": "^1.70.0" },
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
