from __future__ import annotations
from dataclasses import dataclass, field
from typing import Union

Expression = Union[
    "BinOp", "UnaryOp", "Call", "ZeroArgCall", "Pipeline",
    "Lambda", "Compose", "Name", "SelfAttr", "Attribute", "Subscript",
    "StringLiteral", "NumberLiteral", "ListLiteral", "DictLiteral",
    "TernaryOp", "Spread", "ListComp", "DictComp", "SetComp", "Tuple", "Slice", "SetLiteral",
    "ChainedComparison",
]
Statement = Union[
    "FunctionDef", "ClassDef", "Assignment", "AugAssignment",
    "IfStatement", "ForStatement", "DoStatement", "TryStatement",
    "RetStatement", "UseStatement", "AliasStatement",
    "AppendStatement", "ExprStatement",
    "BreakStatement", "ContinueStatement", "RaiseStatement",
    "WithStatement", "GlobalStatement", "NonlocalStatement",
    "UnpackAssignment", "AssertStatement", "DelStatement", "PassStatement",
    "YieldStatement",
]

@dataclass
class Program:
    body: list[Statement]

# --- Statements ---

@dataclass
class FunctionDef:
    name: str          # bare name; @ prefix stripped, is_method=True
    params: list["Param"]
    body: list[Statement]
    is_method: bool
    decorators: list = field(default_factory=list)
    line: int | None = None

@dataclass
class Param:
    name: str
    default: Expression | None = None
    kind: str = "pos"  # "pos", "var" (*args), "kw" (**kwargs)

@dataclass
class ClassDef:
    name: str
    bases: list[str]
    body: list[FunctionDef]
    decorators: list = field(default_factory=list)
    line: int | None = None

@dataclass
class Assignment:
    target: str | Expression    # str for simple names; Expression for subscript/attribute
    value: Expression
    line: int | None = None

@dataclass
class AugAssignment:
    target: str | Expression
    op: str            # +=, -=, *=, /=
    value: Expression
    line: int | None = None

@dataclass
class AppendStatement:
    target: Expression
    value: Expression
    line: int | None = None

@dataclass
class IfStatement:
    condition: Expression
    body: list[Statement]
    elifs: list[tuple[Expression | None, list[Statement]]] = field(default_factory=list)
    # elifs[-1] has condition=None when the last branch is a bare `el`
    line: int | None = None

@dataclass
class ForStatement:
    targets: list[str]
    iterable: Expression
    body: list[Statement]
    else_body: list[Statement] | None = None
    line: int | None = None

@dataclass
class DoStatement:
    condition: Expression
    body: list[Statement]
    else_body: list[Statement] | None = None
    line: int | None = None

@dataclass
class TryStatement:
    body: list[Statement]
    handlers: list["ErrHandler"]
    finally_body: list[Statement] | None = None
    line: int | None = None

@dataclass
class ErrHandler:
    exc_type: str | list[str] | None   # None = bare except; list = (T1, T2, ...)
    name: str | None
    body: list[Statement]

@dataclass
class RetStatement:
    value: Expression | None
    line: int | None = None

@dataclass
class UseStatement:
    imports: list["UseImport"]
    line: int | None = None

@dataclass
class UseImport:
    module: str
    item: str | None = None    # None = import whole module
    alias: str | None = None   # None = no alias

@dataclass
class AliasStatement:
    name: str
    target: Expression
    line: int | None = None

@dataclass
class ExprStatement:
    expr: Expression
    line: int | None = None

@dataclass
class BreakStatement:
    line: int | None = None

@dataclass
class ContinueStatement:
    line: int | None = None

@dataclass
class RaiseStatement:
    exc: Expression | None      # None = bare `raise` (re-raise current exception)
    cause: Expression | None    # None = no `from` clause
    line: int | None = None

@dataclass
class WithStatement:
    items: list[tuple[Expression, str | None]]  # (expr, binding_name); name=None if no `as`
    body: list[Statement]
    line: int | None = None

@dataclass
class GlobalStatement:
    names: list[str]
    line: int | None = None

@dataclass
class NonlocalStatement:
    names: list[str]   # L++ keyword: nl; Python output: nonlocal
    line: int | None = None

@dataclass
class UnpackAssignment:
    targets: list[Expression]   # Name("a") for plain names, Spread(Name("b")) for *b
    value: Expression
    line: int | None = None

@dataclass
class AssertStatement:
    test: Expression
    msg: Expression | None = None
    line: int | None = None

@dataclass
class DelStatement:
    targets: list[Expression]
    line: int | None = None

@dataclass
class PassStatement:
    line: int | None = None

@dataclass
class YieldStatement:
    value: "Expression | None"   # None = bare yield
    is_from: bool = False        # True = yield from
    line: int | None = None

# --- Expressions ---

@dataclass
class BinOp:
    left: Expression
    op: str
    right: Expression

@dataclass
class UnaryOp:
    op: str
    operand: Expression

@dataclass
class Call:
    func: Expression
    args: list[Expression] = field(default_factory=list)
    kwargs: dict[str, Expression] = field(default_factory=dict)

@dataclass
class ZeroArgCall:
    func: Expression

@dataclass
class Pipeline:
    steps: list[Expression]

@dataclass
class Lambda:
    params: list[str]
    body: Expression

@dataclass
class Compose:
    left: Expression
    right: Expression

@dataclass
class Name:
    id: str

@dataclass
class SelfAttr:
    attr: str          # @name → self.name

@dataclass
class Attribute:
    obj: Expression
    attr: str

@dataclass
class Subscript:
    obj: Expression
    key: Expression

@dataclass
class Slice:
    start: Expression | None
    stop: Expression | None
    step: Expression | None = None

@dataclass
class StringLiteral:
    parts: list[str | Expression]   # alternating raw str and Expression

@dataclass
class NumberLiteral:
    value: int | float

@dataclass
class ListLiteral:
    elements: list[Expression]

@dataclass
class DictLiteral:
    pairs: list[tuple[Expression, Expression]]

@dataclass
class SetLiteral:
    elements: list[Expression]

@dataclass
class Tuple:
    elements: list[Expression]

@dataclass
class ListComp:
    elt: Expression
    targets: list[str]
    iter: Expression
    condition: Expression | None = None

@dataclass
class DictComp:
    key: Expression
    value: Expression
    targets: list[str]
    iter: Expression
    condition: Expression | None = None

@dataclass
class SetComp:
    elt: Expression
    targets: list[str]
    iter: Expression
    condition: Expression | None = None

@dataclass
class TernaryOp:
    value: Expression
    condition: Expression
    else_value: Expression

@dataclass
class ChainedComparison:
    operands: list[Expression]   # len == len(ops) + 1
    ops: list[str]

@dataclass
class Spread:
    value: Expression
