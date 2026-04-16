# tests/test_parser.py  (replace stub)
import pytest
from lpp.lexer import Lexer
from lpp.parser import Parser
from lpp.ast_nodes import *

def parse_expr(src: str) -> Expression:
    tokens = Lexer(src).tokenize()
    return Parser(tokens).parse_expression()

def test_parse_number():
    assert parse_expr("42") == NumberLiteral(42)

def test_parse_float():
    assert parse_expr("3.14") == NumberLiteral(3.14)

def test_parse_name():
    assert parse_expr("foo") == Name("foo")

def test_parse_binop_add():
    assert parse_expr("x+y") == BinOp(Name("x"), "+", Name("y"))

def test_parse_binop_compare():
    assert parse_expr("x>5") == BinOp(Name("x"), ">", NumberLiteral(5))

def test_parse_call():
    result = parse_expr("add(x,y)")
    assert isinstance(result, Call)
    assert result.func == Name("add")
    assert result.args == [Name("x"), Name("y")]

def test_parse_zero_arg_call():
    result = parse_expr("foo!")
    assert result == ZeroArgCall(Name("foo"))

def test_parse_method_zero_arg():
    result = parse_expr("msg.upper!")
    assert isinstance(result, ZeroArgCall)
    assert result.func == Attribute(Name("msg"), "upper")

def test_parse_self_attr():
    assert parse_expr("@name") == SelfAttr("name")

def test_parse_lambda_single():
    result = parse_expr("x->x*2")
    assert isinstance(result, Lambda)
    assert result.params == ["x"]
    assert result.body == BinOp(Name("x"), "*", NumberLiteral(2))

def test_parse_lambda_multi():
    result = parse_expr("x,y->x+y")
    assert isinstance(result, Lambda)
    assert result.params == ["x", "y"]

def test_parse_pipeline():
    result = parse_expr("r(10)|ma(x->x*2)|li!")
    assert isinstance(result, Pipeline)
    assert len(result.steps) == 3

def test_parse_string_no_interpolation():
    result = parse_expr('"hello"')
    assert result == StringLiteral(["hello"])

def test_parse_string_with_interpolation():
    result = parse_expr('"hello $name$!"')
    assert isinstance(result, StringLiteral)
    # parts: ["hello ", Name("name"), "!"]
    assert result.parts[0] == "hello "
    assert result.parts[1] == Name("name")
    assert result.parts[2] == "!"

def test_parse_string_escaped_dollar():
    result = parse_expr('"price: $$5"')
    assert result == StringLiteral(["price: $5"])

def test_parse_ternary():
    result = parse_expr("x if cond el y")
    assert isinstance(result, TernaryOp)
    assert result.condition == Name("cond")
    assert result.value == Name("x")
    assert result.else_value == Name("y")

def test_parse_attribute():
    result = parse_expr("obj.attr")
    assert result == Attribute(Name("obj"), "attr")

def test_parse_subscript():
    result = parse_expr("lst[0]")
    assert result == Subscript(Name("lst"), NumberLiteral(0))

def test_ast_nodes_instantiate():
    node = FunctionDef(
        name="add",
        params=[Param("x"), Param("y")],
        body=[Name("x")],
        is_method=False,
    )
    assert node.name == "add"

# Append to tests/test_parser.py

from lpp.parser import Parser
from lpp.lexer import Lexer

def parse_prog(src: str) -> Program:
    tokens = Lexer(src).tokenize()
    return Parser(tokens).parse()

def first(src: str):
    return parse_prog(src).body[0]

def test_parse_assignment():
    node = first("x=42")
    assert isinstance(node, Assignment)
    assert node.target == "x"
    assert node.value == NumberLiteral(42)

def test_parse_aug_assignment():
    node = first("x+=1")
    assert isinstance(node, AugAssignment)
    assert node.op == "+="

def test_parse_function_def():
    node = first("fn add x y\n  x+y\n")
    assert isinstance(node, FunctionDef)
    assert node.name == "add"
    assert node.params == [Param("x"), Param("y")]
    assert not node.is_method

def test_parse_function_default_param():
    node = first("fn greet name loud=0\n  name\n")
    assert isinstance(node, FunctionDef)
    assert node.params[1] == Param("loud", NumberLiteral(0))

def test_parse_method():
    src = "cls Dog\n  fn @bark\n    p!\n"
    node = first(src)
    assert isinstance(node, ClassDef)
    method = node.body[0]
    assert method.is_method
    assert method.name == "bark"

def test_parse_if_else():
    src = "if x>5\n  p(\"big\")\nel\n  p(\"small\")\n"
    node = first(src)
    assert isinstance(node, IfStatement)
    assert len(node.elifs) == 1
    cond, _ = node.elifs[0]
    assert cond is None  # bare el

def test_parse_elif():
    src = "if x>5\n  a\nel x==5\n  b\nel\n  c\n"
    node = first(src)
    assert len(node.elifs) == 2
    assert node.elifs[0][0] == BinOp(Name("x"), "==", NumberLiteral(5))
    assert node.elifs[1][0] is None

def test_parse_for():
    src = "for i in r(10)\n  p(i)\n"
    node = first(src)
    assert isinstance(node, ForStatement)
    assert node.targets == ["i"]

def test_parse_for_tuple_unpack():
    src = "for k,v in d.items!\n  p(k)\n"
    node = first(src)
    assert node.targets == ["k", "v"]

def test_parse_do():
    src = "do x>0\n  x-=1\n"
    node = first(src)
    assert isinstance(node, DoStatement)

def test_parse_try_err():
    src = "try\n  i(val)\nerr ValueError e\n  p(e)\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert node.handlers[0].exc_type == "ValueError"
    assert node.handlers[0].name == "e"

def test_parse_ret():
    src = "fn f\n  ret 42\n"
    node = first(src)
    assert isinstance(node.body[0], RetStatement)
    assert node.body[0].value == NumberLiteral(42)

def test_parse_use_simple():
    node = first("use os,json\n")
    assert isinstance(node, UseStatement)
    assert node.imports[0].module == "os"
    assert node.imports[1].module == "json"

def test_parse_use_alias():
    node = first("use np=numpy\n")
    assert isinstance(node, UseStatement)
    assert node.imports[0].module == "numpy"
    assert node.imports[0].alias == "np"

def test_parse_use_from():
    node = first("use pathlib:Path\n")
    assert isinstance(node, UseStatement)
    assert node.imports[0].module == "pathlib"
    assert node.imports[0].item == "Path"

def test_parse_use_dotted():
    node = first("use os.path\n")
    assert isinstance(node, UseStatement)
    assert node.imports[0] == UseImport("os.path", None, None)

def test_parse_use_dotted_from():
    node = first("use os.path:join\n")
    assert node.imports[0] == UseImport("os.path", "join", None)

def test_parse_alias():
    node = first("alias sq=math.sqrt\n")
    assert isinstance(node, AliasStatement)
    assert node.name == "sq"

def test_parse_append():
    node = first("items<<x\n")
    assert isinstance(node, AppendStatement)
    assert node.target == Name("items")
    assert node.value == Name("x")

def test_try_without_handler_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError, match="err handler"):
        parse_prog("try\n  x=1\n")

def test_parse_compose():
    from lpp.ast_nodes import Compose, Name
    node = parse_expr("f&g")
    assert node == Compose(Name("f"), Name("g"))

def test_parse_compose_chain():
    from lpp.ast_nodes import Compose, Name
    node = parse_expr("f&g&h")
    assert node == Compose(Compose(Name("f"), Name("g")), Name("h"))

def test_parse_error_has_line_and_col():
    from lpp.parser import ParseError
    try:
        parse_prog("fn\n  x\n")  # fn with no name — INDENT follows FN
        assert False, "expected ParseError"
    except ParseError as e:
        assert e.line is not None
        assert e.line >= 1
        assert e.col is not None
        assert e.col >= 1

def test_parse_break():
    src = "for i in r(1)\n  break\n"
    node = first(src)
    assert isinstance(node, ForStatement)
    assert isinstance(node.body[0], BreakStatement)

def test_parse_continue():
    src = "for i in r(1)\n  continue\n"
    node = first(src)
    assert isinstance(node, ForStatement)
    assert isinstance(node.body[0], ContinueStatement)

def test_parse_global():
    node = first("global x,y\n")
    assert isinstance(node, GlobalStatement)
    assert node.names == ["x", "y"]

def test_parse_nonlocal():
    node = first("nl x\n")
    assert isinstance(node, NonlocalStatement)
    assert node.names == ["x"]

def test_parse_raise_bare():
    node = first("raise\n")
    assert isinstance(node, RaiseStatement)
    assert node.exc is None
    assert node.cause is None

def test_parse_raise_expr():
    node = first("raise ValueError(\"oops\")\n")
    assert isinstance(node, RaiseStatement)
    assert isinstance(node.exc, Call)
    assert node.cause is None

def test_parse_raise_from():
    node = first("raise ValueError(\"oops\") from orig\n")
    assert isinstance(node, RaiseStatement)
    assert isinstance(node.exc, Call)
    assert node.cause == Name("orig")

def test_parse_with_as():
    src = "with open(\"f\") as fh\n  p(fh)\n"
    node = first(src)
    assert isinstance(node, WithStatement)
    assert len(node.items) == 1
    expr, name = node.items[0]
    assert isinstance(expr, Call)
    assert name == "fh"

def test_parse_with_no_as():
    src = "with lock!\n  p(\"ok\")\n"
    node = first(src)
    assert isinstance(node, WithStatement)
    assert node.items[0][1] is None

def test_parse_with_multi():
    src = "with open(\"a\") as fa,open(\"b\") as fb\n  p(fa)\n"
    node = first(src)
    assert isinstance(node, WithStatement)
    assert len(node.items) == 2
    assert node.items[0][1] == "fa"
    assert node.items[1][1] == "fb"

def test_parse_try_finally():
    src = "try\n  x=1\nerr\n  x=2\nfin\n  p(\"done\")\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert len(node.handlers) == 1
    assert node.finally_body is not None
    assert len(node.finally_body) == 1

def test_parse_try_only_fin():
    src = "try\n  x=1\nfin\n  p(\"done\")\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert node.handlers == []
    assert node.finally_body is not None

def test_parse_try_err_and_fin():
    src = "try\n  x=1\nerr ValueError e\n  p(e)\nfin\n  p(\"done\")\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert len(node.handlers) == 1
    assert node.finally_body is not None

def test_parse_subscript_assign():
    node = first("d[k]=v\n")
    assert isinstance(node, Assignment)
    assert node.target == Subscript(Name("d"), Name("k"))
    assert node.value == Name("v")

def test_parse_attr_assign():
    node = first("obj.attr=v\n")
    assert isinstance(node, Assignment)
    assert node.target == Attribute(Name("obj"), "attr")
    assert node.value == Name("v")

def test_parse_unpack_assign():
    node = first("a,b=myfn!\n")
    assert isinstance(node, UnpackAssignment)
    assert node.targets == [Name("a"), Name("b")]
    assert node.value == ZeroArgCall(Name("myfn"))

def test_parse_star_unpack():
    node = first("a,*b=lst\n")
    assert isinstance(node, UnpackAssignment)
    assert node.targets[0] == Name("a")
    assert node.targets[1] == Spread(Name("b"))

def test_parse_subscript_aug():
    node = first("d[k]+=1\n")
    assert isinstance(node, AugAssignment)
    assert node.target == Subscript(Name("d"), Name("k"))
    assert node.op == "+="

def test_parse_attr_aug():
    node = first("obj.attr+=1\n")
    assert isinstance(node, AugAssignment)
    assert node.target == Attribute(Name("obj"), "attr")
    assert node.op == "+="
