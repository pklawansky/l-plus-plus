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
    result = parse_expr("x if cond else y")
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
    node = first("def add x y\n  x+y\n")
    assert isinstance(node, FunctionDef)
    assert node.name == "add"
    assert node.params == [Param("x"), Param("y")]
    assert not node.is_method

def test_parse_function_default_param():
    node = first("def greet name loud=0\n  name\n")
    assert isinstance(node, FunctionDef)
    assert node.params[1] == Param("loud", NumberLiteral(0))

def test_parse_method():
    src = "class Dog\n  def @bark\n    p!\n"
    node = first(src)
    assert isinstance(node, ClassDef)
    method = node.body[0]
    assert method.is_method
    assert method.name == "bark"

def test_parse_if_else():
    src = "if x>5\n  p(\"big\")\nelse\n  p(\"small\")\n"
    node = first(src)
    assert isinstance(node, IfStatement)
    assert len(node.elifs) == 1
    cond, _ = node.elifs[0]
    assert cond is None  # bare else

def test_parse_elif():
    src = "if x>5\n  a\nelif x==5\n  b\nelse\n  c\n"
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
    src = "while x>0\n  x-=1\n"
    node = first(src)
    assert isinstance(node, DoStatement)

def test_parse_try_err():
    src = "try\n  i(val)\nexcept ValueError e\n  p(e)\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert node.handlers[0].exc_type == "ValueError"
    assert node.handlers[0].name == "e"

def test_parse_ret():
    src = "def f\n  return 42\n"
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
    with pytest.raises(ParseError, match="except handler"):
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
        parse_prog("def\n  x\n")  # def with no name — INDENT follows DEF
        assert False, "expected ParseError"
    except ParseError as e:
        assert e.line is not None
        assert e.line >= 1
        assert e.col is not None
        assert e.col >= 1

def test_parse_decorated_function():
    from lpp.ast_nodes import FunctionDef, Name
    node = first("@staticmethod\ndef foo x\n  x\n")
    assert isinstance(node, FunctionDef)
    assert node.name == "foo"
    assert node.decorators == [Name("staticmethod")]

def test_parse_stacked_decorators_on_function():
    from lpp.ast_nodes import FunctionDef, Name
    node = first("@classmethod\n@cache\ndef bar cls\n  1\n")
    assert isinstance(node, FunctionDef)
    assert node.decorators == [Name("classmethod"), Name("cache")]

def test_parse_decorated_class():
    from lpp.ast_nodes import ClassDef, Name
    node = first("@dataclass\nclass Point\n  def @init x\n    @x=x\n")
    assert isinstance(node, ClassDef)
    assert node.name == "Point"
    assert node.decorators == [Name("dataclass")]

def test_parse_decorated_method_inside_class():
    from lpp.ast_nodes import ClassDef, Name
    node = first("class Foo\n  @property\n  def @bar\n    @_bar\n")
    assert isinstance(node, ClassDef)
    assert node.body[0].name == "bar"
    assert node.body[0].decorators == [Name("property")]

def test_at_attr_not_before_def_is_unchanged():
    from lpp.ast_nodes import ExprStatement, SelfAttr
    node = first("@x\n")
    assert isinstance(node, ExprStatement)
    assert node.expr == SelfAttr("x")

def test_parse_error_has_expected_field():
    from lpp.parser import ParseError
    try:
        parse_prog("def\n  x\n")
        assert False, "expected ParseError"
    except ParseError as e:
        assert e.expected == "IDENT"

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
    src = "try\n  x=1\nexcept\n  x=2\nfinally\n  p(\"done\")\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert len(node.handlers) == 1
    assert node.finally_body is not None
    assert len(node.finally_body) == 1

def test_parse_try_only_fin():
    src = "try\n  x=1\nfinally\n  p(\"done\")\n"
    node = first(src)
    assert isinstance(node, TryStatement)
    assert node.handlers == []
    assert node.finally_body is not None

def test_parse_try_err_and_fin():
    src = "try\n  x=1\nexcept ValueError e\n  p(e)\nfinally\n  p(\"done\")\n"
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

# --- Error-path tests ---

def test_unclosed_paren_in_call_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError):
        parse_expr("add(1,2")

def test_unclosed_list_literal_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError):
        parse_expr("[1, 2, 3")

def test_unclosed_dict_literal_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError):
        parse_expr("{1: 2")

def test_lambda_no_body_falls_back_to_name():
    # `x->` has no body — the lambda lookahead catches the ParseError and
    # falls back, returning Name("x"). The `->` is left in the token stream
    # but parse_expression stops at the Name.
    node = parse_expr("x->")
    assert node == Name("x")

def test_lambda_multi_param_no_body_falls_back():
    # `x,y->` with no body: lookahead fails, falls back to Name("x").
    node = parse_expr("x,y->")
    assert node == Name("x")

def test_tuple_at_stmt_level():
    node = first("a,b\n")
    assert isinstance(node, ExprStatement)
    assert node.expr == Tuple([Name("a"), Name("b")])

def test_ternary_missing_else_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError):
        parse_expr("x if cond")

def test_function_def_missing_name_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError):
        parse_prog("def\n  x\n")

def test_function_def_missing_body_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError):
        parse_prog("def f\n")

def test_if_missing_body_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError):
        parse_prog("if x\n")

# is / not in operators
# multiple inheritance
def test_parse_multi_inherit():
    node = first("class Foo:Bar,Baz\n  def @init\n    42\n")
    assert isinstance(node, ClassDef)
    assert node.bases == ["Bar", "Baz"]

def test_parse_single_inherit_still_works():
    node = first("class Dog:Animal\n  def @bark\n    42\n")
    assert node.bases == ["Animal"]

# for/else
def test_parse_for_else():
    src = "for i in r(3)\n  p(i)\nelse\n  p(0)\n"
    node = first(src)
    assert isinstance(node, ForStatement)
    assert node.else_body is not None
    assert len(node.else_body) == 1

# set literals
def test_parse_set_literal():
    result = parse_expr("{1,2,3}")
    assert isinstance(result, SetLiteral)
    assert result.elements == [NumberLiteral(1), NumberLiteral(2), NumberLiteral(3)]

def test_parse_set_single():
    result = parse_expr("{42}")
    assert isinstance(result, SetLiteral)

# %= augmented assignment
def test_parse_modulo_assign():
    node = first("x%=3\n")
    assert isinstance(node, AugAssignment)
    assert node.op == "%="
    assert node.value == NumberLiteral(3)

# assert / del
def test_parse_assert():
    node = first("assert x==1\n")
    assert isinstance(node, AssertStatement)
    assert node.test == BinOp(Name("x"), "==", NumberLiteral(1))
    assert node.msg is None

def test_parse_assert_with_msg():
    node = first('assert x==1,"fail"\n')
    assert isinstance(node, AssertStatement)
    assert node.msg == StringLiteral(["fail"])

def test_parse_del():
    node = first("del x\n")
    assert isinstance(node, DelStatement)
    assert node.targets == [Name("x")]

def test_parse_del_multi():
    node = first("del x,y\n")
    assert isinstance(node, DelStatement)
    assert node.targets == [Name("x"), Name("y")]

# slice notation
def test_parse_slice_basic():
    result = parse_expr("lst[0:n]")
    assert result == Subscript(Name("lst"), Slice(NumberLiteral(0), Name("n"), None))

def test_parse_slice_step():
    result = parse_expr("lst[::2]")
    assert result == Subscript(Name("lst"), Slice(None, None, NumberLiteral(2)))

def test_slice_empty_start_stop():
    # Explicitly verify that :: (COLONCOLON token) maps both start and stop to None,
    # with the value after :: becoming the step.  This directly exercises the
    # COLONCOLON branch added to _parse_subscript_key.
    result = parse_expr("a[::2]")
    assert isinstance(result, Subscript)
    assert result.obj == Name("a")
    assert isinstance(result.key, Slice)
    assert result.key.start is None
    assert result.key.stop is None
    assert result.key.step == NumberLiteral(2)

def test_parse_slice_open_end():
    result = parse_expr("lst[1:]")
    assert result == Subscript(Name("lst"), Slice(NumberLiteral(1), None, None))

def test_parse_slice_open_start():
    result = parse_expr("lst[:n]")
    assert result == Subscript(Name("lst"), Slice(None, Name("n"), None))

def test_parse_slice_full():
    result = parse_expr("lst[1:5:2]")
    assert result == Subscript(Name("lst"), Slice(NumberLiteral(1), NumberLiteral(5), NumberLiteral(2)))

def test_subscript_multi_arg():
    # dict[str, int] — comma inside [] produces Tuple key
    result = parse_expr("dict[str, int]")
    assert result == Subscript(Name("dict"), Tuple([Name("str"), Name("int")]))

# *args / **kwargs in function params
def test_parse_params_star_args():
    node = first("def f *args\n  args\n")
    assert isinstance(node, FunctionDef)
    assert node.params == [Param("args", kind="var")]

def test_parse_params_kwargs():
    node = first("def f **kwargs\n  kwargs\n")
    assert node.params == [Param("kwargs", kind="kw")]

def test_parse_params_mixed():
    node = first("def f x *args **kwargs\n  x\n")
    assert node.params == [Param("x"), Param("args", kind="var"), Param("kwargs", kind="kw")]

# tuple literals / multi-value return
def test_parse_return_tuple():
    node = first("return a, b\n")
    assert isinstance(node, RetStatement)
    assert node.value == Tuple([Name("a"), Name("b")])

def test_parse_assign_tuple_rhs():
    node = first("x=1,2,3\n")
    assert isinstance(node, Assignment)
    assert node.value == Tuple([NumberLiteral(1), NumberLiteral(2), NumberLiteral(3)])

def test_parse_tuple_expr_stmt():
    node = first("a,b\n")
    assert isinstance(node, ExprStatement)
    assert node.expr == Tuple([Name("a"), Name("b")])

# list / dict comprehensions
def test_parse_list_comp():
    result = parse_expr("[x*x for x in lst]")
    assert isinstance(result, ListComp)
    assert result.elt == BinOp(Name("x"), "*", Name("x"))
    assert result.targets == ["x"]
    assert result.iter == Name("lst")
    assert result.condition is None

def test_parse_list_comp_with_if():
    result = parse_expr("[x for x in lst if x>0]")
    assert isinstance(result, ListComp)
    assert result.condition == BinOp(Name("x"), ">", NumberLiteral(0))

def test_parse_list_comp_multi_target():
    result = parse_expr("[k for k,v in pairs]")
    assert isinstance(result, ListComp)
    assert result.targets == ["k", "v"]

def test_parse_dict_comp():
    result = parse_expr("{k: v for k,v in pairs}")
    assert isinstance(result, DictComp)
    assert result.key == Name("k")
    assert result.value == Name("v")
    assert result.targets == ["k", "v"]
    assert result.iter == Name("pairs")
    assert result.condition is None

def test_parse_dict_comp_with_if():
    result = parse_expr("{k: v for k,v in pairs if k>0}")
    assert isinstance(result, DictComp)
    assert result.condition == BinOp(Name("k"), ">", NumberLiteral(0))

# ** and //
def test_parse_power():
    assert parse_expr("a**b") == BinOp(Name("a"), "**", Name("b"))

def test_parse_floordiv():
    assert parse_expr("a//b") == BinOp(Name("a"), "//", Name("b"))

def test_parse_power_precedence():
    # a*b**c should be a*(b**c), not (a*b)**c
    result = parse_expr("a*b**c")
    assert result == BinOp(Name("a"), "*", BinOp(Name("b"), "**", Name("c")))

# is / not in operators
def test_parse_is():
    assert parse_expr("x is None") == BinOp(Name("x"), "is", Name("None"))

def test_parse_not_in():
    assert parse_expr("x not in col") == BinOp(Name("x"), "not in", Name("col"))

def test_parse_is_not():
    assert parse_expr("x is not None") == BinOp(Name("x"), "is not", Name("None"))

def test_while_missing_body_raises():
    from lpp.parser import ParseError
    with pytest.raises(ParseError):
        parse_prog("while x\n")

def test_functiondef_decorators_default_empty():
    from lpp.ast_nodes import FunctionDef
    node = FunctionDef("foo", [], [], False)
    assert node.decorators == []

def test_classdef_decorators_default_empty():
    from lpp.ast_nodes import ClassDef
    node = ClassDef("Foo", None, [])
    assert node.decorators == []

def test_is_decorator_context_true_for_simple():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is True

def test_is_decorator_context_true_for_stacked():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@classmethod\n@cache\ndef bar cls\n  1\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is True

def test_is_decorator_context_true_for_class():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@dataclass\nclass Point\n  def @init x\n    @x=x\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is True

def test_is_decorator_context_false_when_no_def_follows():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@x\np(@x)\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is False

def test_is_decorator_context_does_not_advance_position():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.tokens import TokenType
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    p = Parser(tokens)
    pos_before = p.pos
    p._is_decorator_context()
    assert p.pos == pos_before

def test_is_decorator_context_true_for_call_decorator():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@lru_cache(maxsize=128)\ndef fib n\n  n\n").tokenize()
    p = Parser(tokens)
    assert p._is_decorator_context() is True

def test_collect_single_decorator():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.ast_nodes import Name
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    p = Parser(tokens)
    decs = p._collect_decorators()
    assert decs == [Name("staticmethod")]

def test_collect_stacked_decorators():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.ast_nodes import Name
    tokens = Lexer("@classmethod\n@cache\ndef bar cls\n  1\n").tokenize()
    p = Parser(tokens)
    decs = p._collect_decorators()
    assert decs == [Name("classmethod"), Name("cache")]

def test_collect_call_decorator():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.ast_nodes import Call, Name, NumberLiteral
    tokens = Lexer("@lru_cache(maxsize=128)\ndef fib n\n  n\n").tokenize()
    p = Parser(tokens)
    decs = p._collect_decorators()
    assert len(decs) == 1
    assert isinstance(decs[0], Call)
    assert decs[0].func == Name("lru_cache")

def test_collect_decorators_advances_past_at_lines():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    from lpp.tokens import TokenType
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    p = Parser(tokens)
    p._collect_decorators()
    assert p.peek_type() == TokenType.DEF

def test_statement_carries_line():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("x = 1\n").tokenize()
    prog = Parser(tokens).parse()
    assert hasattr(prog.body[0], "line"), "Statement node has no .line attribute"
    assert prog.body[0].line == 1

def test_second_statement_has_correct_line():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("x = 1\ny = 2\n").tokenize()
    prog = Parser(tokens).parse()
    assert prog.body[0].line == 1
    assert prog.body[1].line == 2

def test_statement_inside_block_has_correct_line():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("def f\n  x = 1\n  y = 2\n").tokenize()
    prog = Parser(tokens).parse()
    body = prog.body[0].body          # FunctionDef.body
    assert body[0].line == 2
    assert body[1].line == 3

def test_decorated_functiondef_line_is_decorator_line():
    from lpp.lexer import Lexer
    from lpp.parser import Parser
    tokens = Lexer("@staticmethod\ndef foo x\n  x\n").tokenize()
    prog = Parser(tokens).parse()
    assert prog.body[0].line == 1     # @ is on line 1
