from __future__ import annotations
from dataclasses import dataclass, field
from typing import Union

Expression = Union[
    "BinOp", "UnaryOp", "Call", "ZeroArgCall", "Pipeline",
    "Lambda", "Compose", "Name", "SelfAttr", "Attribute", "Subscript",
    "StringLiteral", "NumberLiteral", "ListLiteral", "DictLiteral",
    "TernaryOp", "Spread", "ListComp", "DictComp", "Tuple", "Slice", "SetLiteral",
]
Statement = Union[
    "FunctionDef", "ClassDef", "Assignment", "AugAssignment",
    "IfStatement", "ForStatement", "DoStatement", "TryStatement",
    "RetStatement", "UseStatement", "AliasStatement",
    "AppendStatement", "ExprStatement",
    "BreakStatement", "ContinueStatement", "RaiseStatement",
    "WithStatement", "GlobalStatement", "NonlocalStatement",
    "UnpackAssignment", "AssertStatement", "DelStatement",
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

@dataclass
class Assignment:
    target: str | Expression    # str for simple names; Expression for subscript/attribute
    value: Expression

@dataclass
class AugAssignment:
    target: str | Expression
    op: str            # +=, -=, *=, /=
    value: Expression

@dataclass
class AppendStatement:
    target: Expression
    value: Expression

@dataclass
class IfStatement:
    condition: Expression
    body: list[Statement]
    elifs: list[tuple[Expression | None, list[Statement]]] = field(default_factory=list)
    # elifs[-1] has condition=None when the last branch is a bare `el`

@dataclass
class ForStatement:
    targets: list[str]
    iterable: Expression
    body: list[Statement]
    else_body: list[Statement] | None = None

@dataclass
class DoStatement:
    condition: Expression
    body: list[Statement]

@dataclass
class TryStatement:
    body: list[Statement]
    handlers: list["ErrHandler"]
    finally_body: list[Statement] | None = None

@dataclass
class ErrHandler:
    exc_type: str | None
    name: str | None
    body: list[Statement]

@dataclass
class RetStatement:
    value: Expression | None

@dataclass
class UseStatement:
    imports: list["UseImport"]

@dataclass
class UseImport:
    module: str
    item: str | None = None    # None = import whole module
    alias: str | None = None   # None = no alias

@dataclass
class AliasStatement:
    name: str
    target: Expression

@dataclass
class ExprStatement:
    expr: Expression

@dataclass
class BreakStatement:
    pass

@dataclass
class ContinueStatement:
    pass

@dataclass
class RaiseStatement:
    exc: Expression | None      # None = bare `raise` (re-raise current exception)
    cause: Expression | None    # None = no `from` clause

@dataclass
class WithStatement:
    items: list[tuple[Expression, str | None]]  # (expr, binding_name); name=None if no `as`
    body: list[Statement]

@dataclass
class GlobalStatement:
    names: list[str]

@dataclass
class NonlocalStatement:
    names: list[str]   # L++ keyword: nl; Python output: nonlocal

@dataclass
class UnpackAssignment:
    targets: list[Expression]   # Name("a") for plain names, Spread(Name("b")) for *b
    value: Expression

@dataclass
class AssertStatement:
    test: Expression
    msg: Expression | None = None

@dataclass
class DelStatement:
    targets: list[Expression]

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
class TernaryOp:
    value: Expression
    condition: Expression
    else_value: Expression

@dataclass
class Spread:
    value: Expression
