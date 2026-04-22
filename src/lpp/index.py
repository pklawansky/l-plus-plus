# src/lpp/index.py
from __future__ import annotations
from dataclasses import dataclass
from .lexer import Lexer, LexError
from .parser import Parser, ParseError
from .ast_nodes import Program, FunctionDef, ClassDef, Assignment, AnnotationStatement


@dataclass
class Symbol:
    name: str
    kind: str   # "function" | "class" | "variable"
    uri: str
    line: int


def _extract_symbols(tree: Program, uri: str) -> list[Symbol]:
    symbols = []
    for node in tree.body:
        if isinstance(node, FunctionDef):
            symbols.append(Symbol(node.name, "function", uri, node.line or 1))
        elif isinstance(node, ClassDef):
            symbols.append(Symbol(node.name, "class", uri, node.line or 1))
        elif isinstance(node, Assignment) and isinstance(node.target, str):
            symbols.append(Symbol(node.target, "variable", uri, node.line or 1))
        elif isinstance(node, AnnotationStatement) and isinstance(node.target, str):
            symbols.append(Symbol(node.target, "variable", uri, node.line or 1))
    return symbols


class WorkspaceIndex:
    def __init__(self) -> None:
        self._symbols: dict[str, list[Symbol]] = {}

    def index_file(self, uri: str, source: str) -> None:
        try:
            tokens = Lexer(source).tokenize()
            tree = Parser(tokens).parse()
            self._symbols[uri] = _extract_symbols(tree, uri)
        except (LexError, ParseError):
            pass

    def all_symbols(self) -> list[Symbol]:
        return [s for syms in self._symbols.values() for s in syms]

    def find(self, name: str) -> list[Symbol]:
        return [s for s in self.all_symbols() if s.name == name]
