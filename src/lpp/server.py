from __future__ import annotations
import glob
import os
from pygls.lsp.server import LanguageServer
from lsprotocol.types import (
    INITIALIZED,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_HOVER,
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    DefinitionParams,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    Hover,
    HoverParams,
    InitializedParams,
    Location,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
)
from .lexer import Lexer, LexError
from .parser import Parser, ParseError
from .prelude import PRELUDE
from .tokens import KEYWORDS
from .index import WorkspaceIndex
from .scope import resolve_scope

server = LanguageServer("lpp-server", "v0.1")
_index = WorkspaceIndex()

_BUILTIN_DOCS: dict[str, str] = {
    "p":   "p(...) → print(...)",
    "l":   "l(x) → len(x)",
    "r":   "r(n) → range(n)",
    "s":   "s(x) → str(x)",
    "i":   "i(x) → int(x)",
    "f":   "f(x) → float(x)",
    "b":   "b(x) → bool(x)",
    "t":   "t(x) → type(x)",
    "li":  "li(x) → list(x)",
    "di":  "di(x) → dict(x)",
    "se":  "se(x) → set(x)",
    "tu":  "tu(x) → tuple(x)",
    "en":  "en(x) → enumerate(x)",
    "zi":  "zi(*iterables) → zip(*iterables)",
    "ma":  "ma(f, x) → map(f, x)",
    "fi":  "fi(f, x) → filter(f, x)",
    "so":  "so(x) → sorted(x)",
    "rv":  "rv(x) → reversed(x)",
    "su":  "su(x) → sum(x)",
    "mn":  "mn(*args) → min(*args)",
    "mx":  "mx(*args) → max(*args)",
    "ab":  "ab(x) → abs(x)",
    "ro":  "ro(x, n) → round(x, n)",
    "an":  "an(x) → any(x)",
    "al":  "al(x) → all(x)",
    "nx":  "nx(x) → next(x)",
    "ip":  "ip(prompt) → input(prompt)",
    "op":  "op(path, mode) → open(path, mode)",
    "rp":  "rp(x) → repr(x)",
    "ga":  "ga(obj, name) → getattr(obj, name)",
    "sa":  "sa(obj, name, val) → setattr(obj, name, val)",
    "ha":  "ha(obj, name) → hasattr(obj, name)",
    "od":  "od(c) → ord(c)",
    "ch":  "ch(n) → chr(n)",
    "pw":  "pw(x, y) → pow(x, y)",
    "hx":  "hx(n) → hex(n)",
    "isa": "isa(obj, T) → isinstance(obj, T)",
    "sc":  "sc(A, B) → issubclass(A, B)",
}

_KEYWORD_DOCS: dict[str, str] = {
    "def":      "def name(params): → define a function",
    "class":    "class Name: → define a class",
    "if":       "if cond: → conditional branch",
    "elif":     "elif cond: → else-if branch",
    "else":     "else: → fallback branch",
    "for":      "for x in iter: → iterate over a sequence",
    "in":       "in → membership test or for-loop target",
    "while":    "while cond: → loop while condition is true",
    "return":   "return expr → return value from function",
    "try":      "try: → begin exception handler block",
    "except":   "except Type as e: → catch an exception",
    "use":      "use module → import a module",
    "alias":    "alias name = expr → bind an alias",
    "break":    "break → exit the current loop",
    "continue": "continue → skip to next loop iteration",
    "raise":    "raise exc → raise an exception",
    "with":     "with expr as name: → context manager",
    "as":       "as name → bind result of with/except",
    "finally":  "finally: → always-run cleanup block",
    "global":   "global name → declare module-level variable",
    "nl":       "nl → nonlocal declaration",
    "from":     "from module use name → selective import",
    "is":       "is → identity comparison (a is b)",
    "not":      "not expr → logical negation",
    "assert":   "assert expr → runtime assertion",
    "del":      "del name → delete a name binding",
    "pass":     "pass → no-op placeholder statement",
    "yield":    "yield expr → yield a value from a generator",
}


def _word_at(source: str, line: int, character: int) -> str:
    lines = source.splitlines()
    if line >= len(lines):
        return ""
    text = lines[line]
    start = character
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
        start -= 1
    end = character
    while end < len(text) and (text[end].isalnum() or text[end] == "_"):
        end += 1
    return text[start:end]


def _is_call_site(source: str, line: int, character: int) -> bool:
    lines = source.splitlines()
    if line >= len(lines):
        return False
    text = lines[line]
    end = character
    while end < len(text) and (text[end].isalnum() or text[end] == "_"):
        end += 1
    return text[end:].lstrip().startswith(("(", "!"))


def _validate(ls: LanguageServer, uri: str, source: str) -> None:
    diagnostics: list[Diagnostic] = []
    try:
        tokens = Lexer(source).tokenize()
        Parser(tokens).parse()
    except (LexError, ParseError) as e:
        ln = max((e.line or 1) - 1, 0)
        col = max((e.col or 1) - 1, 0)
        diagnostics.append(
            Diagnostic(
                range=Range(
                    start=Position(line=ln, character=col),
                    end=Position(line=ln, character=col + 1),
                ),
                message=str(e),
                severity=DiagnosticSeverity.Error,
            )
        )
    ls.publish_diagnostics(uri, diagnostics)


@server.feature(INITIALIZED)
def initialized(ls: LanguageServer, params: InitializedParams) -> None:
    for folder in ls.workspace.folders.values():
        root = folder.uri.removeprefix("file:///").replace("/", os.sep)
        for path in glob.glob(os.path.join(root, "**", "*.lpp"), recursive=True):
            try:
                uri = "file:///" + path.replace(os.sep, "/")
                with open(path, encoding="utf-8") as fh:
                    _index.index_file(uri, fh.read())
            except OSError:
                pass


@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams) -> None:
    uri = params.text_document.uri
    source = params.text_document.text
    _index.index_file(uri, source)
    _validate(ls, uri, source)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams) -> None:
    uri = params.text_document.uri
    source = ls.workspace.get_text_document(uri).source
    _index.index_file(uri, source)
    _validate(ls, uri, source)


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: LanguageServer, params: HoverParams) -> Hover | None:
    doc = ls.workspace.get_text_document(params.text_document.uri)
    source = doc.source
    ln = params.position.line
    ch = params.position.character
    word = _word_at(source, ln, ch)
    if not word:
        return None

    if word in _BUILTIN_DOCS and _is_call_site(source, ln, ch):
        text = _BUILTIN_DOCS[word]
    elif word in _KEYWORD_DOCS:
        text = _KEYWORD_DOCS[word]
    else:
        syms = _index.find(word)
        if not syms:
            return None
        sym = syms[0]
        try:
            sym_doc = ls.workspace.get_text_document(sym.uri)
            sym_lines = sym_doc.source.splitlines()
            text = sym_lines[sym.line - 1].strip() if 0 < sym.line <= len(sym_lines) else f"{sym.name} ({sym.kind})"
        except Exception:
            text = f"{sym.name} ({sym.kind})"

    return Hover(contents=MarkupContent(kind=MarkupKind.PlainText, value=text))


@server.feature(TEXT_DOCUMENT_DEFINITION)
def definition(ls: LanguageServer, params: DefinitionParams) -> list[Location] | None:
    doc = ls.workspace.get_text_document(params.text_document.uri)
    source = doc.source
    word = _word_at(source, params.position.line, params.position.character)
    if not word:
        return None
    syms = _index.find(word)
    if not syms:
        return None
    return [
        Location(
            uri=sym.uri,
            range=Range(
                start=Position(line=sym.line - 1, character=0),
                end=Position(line=sym.line - 1, character=0),
            ),
        )
        for sym in syms
    ]


@server.feature(
    TEXT_DOCUMENT_COMPLETION,
    CompletionOptions(trigger_characters=[]),
)
def completion(ls: LanguageServer, params: CompletionParams) -> CompletionList:
    doc = ls.workspace.get_text_document(params.text_document.uri)
    source = doc.source
    ln = params.position.line

    local_names: list[str] = []
    try:
        tokens = Lexer(source).tokenize()
        tree = Parser(tokens).parse()
        local_names = resolve_scope(tree, ln + 1)  # LSP 0-indexed -> 1-indexed
    except (LexError, ParseError):
        pass

    items: list[CompletionItem] = []
    seen: set[str] = set()

    def _add(name: str, kind: CompletionItemKind) -> None:
        if name not in seen:
            seen.add(name)
            items.append(CompletionItem(label=name, kind=kind))

    for kw in KEYWORDS:
        _add(kw, CompletionItemKind.Keyword)
    for alias in PRELUDE:
        _add(alias, CompletionItemKind.Function)
    _kind_map = {
        "function": CompletionItemKind.Function,
        "class": CompletionItemKind.Class,
        "variable": CompletionItemKind.Variable,
    }
    for sym in _index.all_symbols():
        _add(sym.name, _kind_map.get(sym.kind, CompletionItemKind.Variable))
    for name in local_names:
        _add(name, CompletionItemKind.Variable)

    return CompletionList(is_incomplete=False, items=items)


if __name__ == "__main__":
    server.start_io()
