# src/lpp/scope.py
from __future__ import annotations
from .ast_nodes import (
    Program, Statement, FunctionDef, ClassDef,
    Assignment, AugAssignment, ForStatement, IfStatement,
    DoStatement, TryStatement, WithStatement, UnpackAssignment, Name,
)


def resolve_scope(tree: Program, line: int) -> list[str]:
    """Return the names visible at *line* (1-indexed) in *tree*.

    Rules:
    - Find the innermost FunctionDef or ClassDef whose node.line <= line.
    - FunctionDef  → params + all locally assigned/defined names (body walk).
    - ClassDef     → method names + class-level assignment targets.
    - Module level → all top-level function/class names + top-level variables.
    """
    enclosing = None
    for node in tree.body:
        if isinstance(node, (FunctionDef, ClassDef)):
            if (node.line or 0) <= line:
                enclosing = node

    if enclosing is None:
        # Module-level scope
        names: list[str] = []
        for node in tree.body:
            if isinstance(node, (FunctionDef, ClassDef)):
                names.append(node.name)
            elif isinstance(node, Assignment) and isinstance(node.target, str):
                names.append(node.target)
        return list(dict.fromkeys(names))

    if isinstance(enclosing, FunctionDef):
        names = [p.name for p in enclosing.params]
        _collect_body_names(enclosing.body, names)
        return list(dict.fromkeys(names))

    # ClassDef
    names = []
    for node in enclosing.body:
        if isinstance(node, FunctionDef):
            names.append(node.name)
        elif isinstance(node, Assignment) and isinstance(node.target, str):
            names.append(node.target)
    return list(dict.fromkeys(names))


def _collect_body_names(body: list[Statement], names: list[str]) -> None:
    """Recursively collect all names introduced in *body*."""
    for node in body:
        if isinstance(node, Assignment) and isinstance(node.target, str):
            names.append(node.target)
        elif isinstance(node, AugAssignment) and isinstance(node.target, str):
            names.append(node.target)
        elif isinstance(node, ForStatement):
            names.extend(node.targets)
            _collect_body_names(node.body, names)
            if node.else_body:
                _collect_body_names(node.else_body, names)
        elif isinstance(node, FunctionDef):
            names.append(node.name)
        elif isinstance(node, IfStatement):
            _collect_body_names(node.body, names)
            for _cond, elif_body in node.elifs:
                _collect_body_names(elif_body, names)
        elif isinstance(node, DoStatement):
            _collect_body_names(node.body, names)
            if node.else_body:
                _collect_body_names(node.else_body, names)
        elif isinstance(node, TryStatement):
            _collect_body_names(node.body, names)
            for handler in node.handlers:
                if handler.name:
                    names.append(handler.name)
                _collect_body_names(handler.body, names)
            if node.finally_body:
                _collect_body_names(node.finally_body, names)
        elif isinstance(node, WithStatement):
            for _expr, name in node.items:
                if name:
                    names.append(name)
            _collect_body_names(node.body, names)
        elif isinstance(node, UnpackAssignment):
            for t in node.targets:
                if isinstance(t, Name):
                    names.append(t.id)
