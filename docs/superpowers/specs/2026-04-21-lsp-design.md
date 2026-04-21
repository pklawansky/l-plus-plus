# L++ LSP — Design Spec

**Date:** 2026-04-21  
**Status:** Approved

---

## Goal

Add a Language Server Protocol (LSP) server to the L++ repo that provides full IDE features for `.lpp` files in VS Code: diagnostics (red squiggles on lex/parse errors), hover documentation, go-to-definition (cross-file), and completions (keywords, built-ins, workspace symbols, local scope).

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Create | `src/lpp/server.py` | pygls LSP server — all protocol handlers |
| Create | `src/lpp/index.py` | Workspace symbol index (cross-file) |
| Create | `src/lpp/scope.py` | Per-document scope resolver (local names) |
| Create | `client/extension.js` | VS Code extension entry point |
| Modify | `package.json` | Add `main`, `activationEvents`, npm dep |
| Modify | `pyproject.toml` | Add `pygls>=1.3` to dependencies |
| Create | `tests/test_index.py` | Unit tests for workspace index |
| Create | `tests/test_scope.py` | Unit tests for scope resolver |

---

## Architecture

```
VS Code ←→ client/extension.js  (vscode-languageclient, JSON-RPC over stdio)
                    ↓
           src/lpp/server.py    (pygls, handles all LSP requests)
           ├── index.py         (workspace symbols, updated on every file change)
           └── scope.py         (local names at cursor, queried per-request)
```

The server runs as `python -m lpp.server`. `lpp` must be pip-installed. `pygls` is the only new Python dependency. `vscode-languageclient` is the only npm dependency and is not included in the pip package.

---

## Feature: Diagnostics

**Triggers:** `textDocument/didOpen`, `textDocument/didChange`

Run `Lexer(source).tokenize()` then `Parser(tokens).parse()`. On `LexError` or `ParseError`, publish one `Diagnostic` at `(err.line - 1, err.col - 1)` (LSP is 0-indexed) with `DiagnosticSeverity.Error`. On success, publish an empty list to clear previous squiggles. No changes to existing compiler code needed — `line`, `col`, and `expected` are already on both error types.

---

## Feature: Hover

**Trigger:** `textDocument/hover`

Extract the word under the cursor. Check in order:

1. **Built-in** — word matches one of the 38 prelude aliases and next non-whitespace char is `(` or `!`: return static signature doc (e.g., `p(x) → print(x)`)
2. **Keyword** — word is a known L++ keyword: return one-line description (e.g., `use → import statement`)
3. **User symbol** — look up word in workspace index; if found, return the source line where it's defined

Built-in and keyword docs are a static dict in `server.py`.

---

## Feature: Go-to-definition

**Trigger:** `textDocument/definition`

1. Get the word under cursor
2. Look up word in workspace index
3. Return all matching `Location` objects (file URI + line); VS Code shows a picker if multiple
4. Return null if not found

Local variables are not navigated — within a file the definition is visible; cross-file navigation targets top-level symbols only.

---

## Feature: Completions

**Trigger:** any identifier character (no special trigger)

Four sources, merged and deduplicated by name:

1. **Keywords** — static list of all 28 L++ keywords; `CompletionItemKind.Keyword`
2. **Built-ins** — static list of all 38 prelude aliases; `CompletionItemKind.Function`
3. **Workspace symbols** — all symbols from the index with their kind (`Function`, `Class`, `Variable`)
4. **Local scope** — names at cursor from `scope.py`; `CompletionItemKind.Variable`

---

## Module: `src/lpp/index.py`

### `Symbol` dataclass

```
name: str
kind: str        # "function" | "class" | "variable"
uri: str
line: int
```

### `WorkspaceIndex`

- `_symbols: dict[str, list[Symbol]]` — keyed by file URI
- `index_file(uri, source)` — parse source, extract top-level symbols, update entry; on parse failure keep old entry
- `all_symbols() -> list[Symbol]`
- `find(name) -> list[Symbol]`

**Extraction rules** (top-level `Program.body` only, no deep walk):
- `FunctionDef` → `kind="function"`, `name=node.name`, `line=node.line`
- `ClassDef` → `kind="class"`, `name=node.name`, `line=node.line`
- `Assignment` where target is a `Name` node → `kind="variable"`, `name=node.target.name`, `line=node.line`

---

## Module: `src/lpp/scope.py`

### `resolve_scope(tree: Program, line: int) -> list[str]`

Returns names in scope at the given line. Best-effort heuristic — errs toward returning more names than fewer.

Walk strategy:
1. Scan `Program.body` for the last `FunctionDef` or `ClassDef` whose `.line` is ≤ cursor line — that is the enclosing scope
2. If enclosing scope is a `FunctionDef`: collect param names, then walk `body` collecting `Assignment` targets (where target is `Name`), `AugAssignment` targets, and `ForStatement` loop variable names
3. If enclosing scope is a `ClassDef`: collect method names (nested `FunctionDef` names) and class-level `Assignment` target names
4. If no enclosing scope found (cursor is at module level): collect all top-level `Assignment` target names and `FunctionDef`/`ClassDef` names from `Program.body`

---

## Module: `client/extension.js`

```javascript
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');

let client;

function activate(context) {
    const serverOptions = {
        command: 'python',
        args: ['-m', 'lpp.server'],
        transport: TransportKind.stdio,
    };
    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'lpp' }],
    };
    client = new LanguageClient('lpp', 'L++ Language Server', serverOptions, clientOptions);
    context.subscriptions.push(client.start());
}

function deactivate() {
    if (client) return client.stop();
}

module.exports = { activate, deactivate };
```

---

## `package.json` changes

Add:
```json
"main": "client/extension.js",
"activationEvents": ["onLanguage:lpp"],
"dependencies": {
  "vscode-languageclient": "^9.0.0"
}
```

---

## `pyproject.toml` changes

Add to `[project]`:
```toml
dependencies = ["pygls>=1.3"]
```

---

## Testing

- `tests/test_index.py` — unit tests for `WorkspaceIndex.index_file` and `find`; no LSP protocol involved
- `tests/test_scope.py` — unit tests for `resolve_scope` at various cursor positions
- `server.py` — manual verification in VS Code (diagnostics, hover, completions, go-to-definition)
- All 317 existing tests remain unaffected

---

## Installation

1. `pip install pygls` (or `pip install -e .` after pyproject.toml update)
2. `npm install` in repo root
3. Open repo in VS Code → F5 (or `code --extensionDevelopmentPath=C:\Repos\Personal\l-plus-plus`)

---

## What Does Not Change

- `lexer.py`, `parser.py`, `transpiler.py`, `ast_nodes.py` — no modifications
- `compile_lpp` public API — unchanged
- All existing tests — unaffected
