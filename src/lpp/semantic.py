from __future__ import annotations
from .ast_nodes import (
    Program, Statement, Expression,
    FunctionDef, ClassDef, Assignment, AugAssignment, AppendStatement,
    ForStatement, IfStatement, DoStatement, TryStatement, WithStatement,
    UnpackAssignment, AliasStatement, UseStatement, AnnotationStatement,
    ExprStatement, RetStatement, RaiseStatement, AssertStatement,
    GlobalStatement, NonlocalStatement, YieldStatement, DelStatement,
    Name, SelfAttr, Attribute, Subscript, BinOp, UnaryOp, Call,
    ZeroArgCall, Pipeline, Lambda, Compose, StringLiteral, NumberLiteral,
    ListLiteral, DictLiteral, TernaryOp, Spread, ListComp, DictComp,
    SetComp, Tuple, Slice, SetLiteral, ChainedComparison,
)
from .prelude import PRELUDE

_BUILTINS: frozenset[str] = frozenset(PRELUDE) | frozenset({
    "None", "True", "False",
    # Python built-in types usable as callables (e.g. defaultdict(int))
    "int", "str", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "complex", "type", "object", "super",
    "NotImplemented", "Ellipsis",
    "Exception", "BaseException", "ValueError", "TypeError", "RuntimeError",
    "AttributeError", "KeyError", "IndexError", "StopIteration", "OSError",
    "FileNotFoundError", "PermissionError", "NotImplementedError",
    "ZeroDivisionError", "OverflowError", "AssertionError", "ImportError",
    "NameError", "RecursionError", "SystemExit", "KeyboardInterrupt",
})


def check_names(tree: Program) -> list[tuple[str, int]]:
    """Return (name, line) for each name used but not declared in scope."""
    errors: list[tuple[str, int]] = []
    module_scope = _module_scope(tree)
    for stmt in tree.body:
        _check_stmt(stmt, module_scope, errors)
    return errors


def _module_scope(tree: Program) -> frozenset[str]:
    names: set[str] = set(_BUILTINS)
    for stmt in tree.body:
        _collect_decls(stmt, names)
    return frozenset(names)


def _collect_decls(stmt: Statement, into: set[str]) -> None:
    """Collect names introduced by a statement (not recursive into bodies)."""
    if isinstance(stmt, (FunctionDef, ClassDef)):
        into.add(stmt.name)
    elif isinstance(stmt, Assignment) and isinstance(stmt.target, str):
        into.add(stmt.target)
    elif isinstance(stmt, AugAssignment) and isinstance(stmt.target, str):
        into.add(stmt.target)
    elif isinstance(stmt, ForStatement):
        into.update(stmt.targets)
    elif isinstance(stmt, TryStatement):
        for h in stmt.handlers:
            if h.name:
                into.add(h.name)
    elif isinstance(stmt, WithStatement):
        for _, name in stmt.items:
            if name:
                into.add(name)
    elif isinstance(stmt, UseStatement):
        for imp in stmt.imports:
            into.add(imp.alias or imp.item or imp.module)
    elif isinstance(stmt, AliasStatement):
        into.add(stmt.name)
    elif isinstance(stmt, UnpackAssignment):
        for t in stmt.targets:
            if isinstance(t, Name):
                into.add(t.id)
    elif isinstance(stmt, AnnotationStatement) and isinstance(stmt.target, str):
        into.add(stmt.target)
    elif isinstance(stmt, GlobalStatement):
        into.update(stmt.names)
    elif isinstance(stmt, NonlocalStatement):
        into.update(stmt.names)


def _check_stmt(stmt: Statement, scope: frozenset[str], errors: list[tuple[str, int]]) -> None:
    line: int = getattr(stmt, "line", None) or 0

    if isinstance(stmt, FunctionDef):
        local: set[str] = set(scope)
        if stmt.is_method:
            local.add("self")
        local.update(p.name for p in stmt.params)
        for s in stmt.body:
            _collect_decls(s, local)
        fn_scope = frozenset(local)
        for s in stmt.body:
            _check_stmt(s, fn_scope, errors)

    elif isinstance(stmt, ClassDef):
        local = set(scope)
        for m in stmt.body:
            _collect_decls(m, local)
        cls_scope = frozenset(local)
        for m in stmt.body:
            _check_stmt(m, cls_scope, errors)

    elif isinstance(stmt, Assignment):
        _check_expr(stmt.value, scope, line, errors)
        if not isinstance(stmt.target, str):
            _check_expr(stmt.target, scope, line, errors)

    elif isinstance(stmt, AugAssignment):
        if isinstance(stmt.target, str):
            if stmt.target not in scope:
                errors.append((stmt.target, line))
        else:
            _check_expr(stmt.target, scope, line, errors)
        _check_expr(stmt.value, scope, line, errors)

    elif isinstance(stmt, AppendStatement):
        _check_expr(stmt.target, scope, line, errors)
        _check_expr(stmt.value, scope, line, errors)

    elif isinstance(stmt, ExprStatement):
        _check_expr(stmt.expr, scope, line, errors)

    elif isinstance(stmt, RetStatement):
        if stmt.value is not None:
            _check_expr(stmt.value, scope, line, errors)

    elif isinstance(stmt, RaiseStatement):
        if stmt.exc:
            _check_expr(stmt.exc, scope, line, errors)
        if stmt.cause:
            _check_expr(stmt.cause, scope, line, errors)

    elif isinstance(stmt, AssertStatement):
        _check_expr(stmt.test, scope, line, errors)
        if stmt.msg is not None:
            _check_expr(stmt.msg, scope, line, errors)

    elif isinstance(stmt, DelStatement):
        for t in stmt.targets:
            _check_expr(t, scope, line, errors)

    elif isinstance(stmt, YieldStatement):
        if stmt.value is not None:
            _check_expr(stmt.value, scope, line, errors)

    elif isinstance(stmt, AnnotationStatement):
        _check_expr(stmt.annotation, scope, line, errors)

    elif isinstance(stmt, IfStatement):
        _check_expr(stmt.condition, scope, line, errors)
        for s in stmt.body:
            _check_stmt(s, scope, errors)
        for cond, body in stmt.elifs:
            if cond is not None:
                _check_expr(cond, scope, line, errors)
            for s in body:
                _check_stmt(s, scope, errors)

    elif isinstance(stmt, ForStatement):
        _check_expr(stmt.iterable, scope, line, errors)
        local = set(scope)
        local.update(stmt.targets)
        loop_scope = frozenset(local)
        for s in stmt.body:
            _check_stmt(s, loop_scope, errors)
        if stmt.else_body:
            for s in stmt.else_body:
                _check_stmt(s, loop_scope, errors)

    elif isinstance(stmt, DoStatement):
        local = set(scope)
        for s in stmt.body:
            _collect_decls(s, local)
        loop_scope = frozenset(local)
        for s in stmt.body:
            _check_stmt(s, loop_scope, errors)
        _check_expr(stmt.condition, loop_scope, line, errors)
        if stmt.else_body:
            for s in stmt.else_body:
                _check_stmt(s, loop_scope, errors)

    elif isinstance(stmt, TryStatement):
        for s in stmt.body:
            _check_stmt(s, scope, errors)
        for handler in stmt.handlers:
            local = set(scope)
            if handler.name:
                local.add(handler.name)
            for s in handler.body:
                _check_stmt(s, frozenset(local), errors)
        if stmt.finally_body:
            for s in stmt.finally_body:
                _check_stmt(s, scope, errors)

    elif isinstance(stmt, WithStatement):
        local = set(scope)
        for expr, name in stmt.items:
            _check_expr(expr, frozenset(local), line, errors)
            if name:
                local.add(name)
        with_scope = frozenset(local)
        for s in stmt.body:
            _check_stmt(s, with_scope, errors)

    elif isinstance(stmt, UnpackAssignment):
        _check_expr(stmt.value, scope, line, errors)

    elif isinstance(stmt, AliasStatement):
        _check_expr(stmt.target, scope, line, errors)


def _check_expr(expr: Expression, scope: frozenset[str], line: int, errors: list[tuple[str, int]]) -> None:
    if expr is None:
        return
    if isinstance(expr, Name):
        if expr.id not in scope:
            errors.append((expr.id, line))
    elif isinstance(expr, (SelfAttr, NumberLiteral)):
        pass
    elif isinstance(expr, StringLiteral):
        for part in expr.parts:
            if not isinstance(part, str):
                _check_expr(part, scope, line, errors)
    elif isinstance(expr, Attribute):
        _check_expr(expr.obj, scope, line, errors)
    elif isinstance(expr, Subscript):
        _check_expr(expr.obj, scope, line, errors)
        _check_expr(expr.key, scope, line, errors)
    elif isinstance(expr, BinOp):
        _check_expr(expr.left, scope, line, errors)
        _check_expr(expr.right, scope, line, errors)
    elif isinstance(expr, UnaryOp):
        _check_expr(expr.operand, scope, line, errors)
    elif isinstance(expr, Call):
        _check_expr(expr.func, scope, line, errors)
        for arg in expr.args:
            _check_expr(arg, scope, line, errors)
        for val in expr.kwargs.values():
            _check_expr(val, scope, line, errors)
    elif isinstance(expr, ZeroArgCall):
        _check_expr(expr.func, scope, line, errors)
    elif isinstance(expr, Pipeline):
        for step in expr.steps:
            _check_expr(step, scope, line, errors)
    elif isinstance(expr, Compose):
        _check_expr(expr.left, scope, line, errors)
        _check_expr(expr.right, scope, line, errors)
    elif isinstance(expr, Lambda):
        local: set[str] = set(scope)
        local.update(expr.params)
        _check_expr(expr.body, frozenset(local), line, errors)
    elif isinstance(expr, TernaryOp):
        _check_expr(expr.condition, scope, line, errors)
        _check_expr(expr.value, scope, line, errors)
        _check_expr(expr.else_value, scope, line, errors)
    elif isinstance(expr, Spread):
        _check_expr(expr.value, scope, line, errors)
    elif isinstance(expr, (ListLiteral, Tuple, SetLiteral)):
        for item in expr.elements:
            _check_expr(item, scope, line, errors)
    elif isinstance(expr, DictLiteral):
        for k, v in expr.pairs:
            _check_expr(k, scope, line, errors)
            _check_expr(v, scope, line, errors)
    elif isinstance(expr, (ListComp, SetComp)):
        local = set(scope)
        local.update(expr.targets)
        comp_scope = frozenset(local)
        _check_expr(expr.iter, scope, line, errors)
        _check_expr(expr.elt, comp_scope, line, errors)
        if expr.condition is not None:
            _check_expr(expr.condition, comp_scope, line, errors)
    elif isinstance(expr, DictComp):
        local = set(scope)
        local.update(expr.targets)
        comp_scope = frozenset(local)
        _check_expr(expr.iter, scope, line, errors)
        _check_expr(expr.key, comp_scope, line, errors)
        _check_expr(expr.value, comp_scope, line, errors)
        if expr.condition is not None:
            _check_expr(expr.condition, comp_scope, line, errors)
    elif isinstance(expr, Slice):
        for part in (expr.start, expr.stop, expr.step):
            if part is not None:
                _check_expr(part, scope, line, errors)
    elif isinstance(expr, ChainedComparison):
        for operand in expr.operands:
            _check_expr(operand, scope, line, errors)
