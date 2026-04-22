# tests/test_transpiler.py
import re
import pytest
from lpp import compile_lpp

def py(src: str) -> str:
    """Compile L++ and strip prelude for test clarity."""
    full = compile_lpp(src)
    # Strip prelude lines (up to first blank line after prelude)
    lines = full.split("\n")
    start = next(i for i, l in enumerate(lines) if l == "") + 1
    # Remove lpp line markers for test compatibility
    result_lines = []
    for line in lines[start:]:
        # Strip # lpp:N comments from the end of lines
        line = line.rstrip()
        line = re.sub(r'  # lpp:\d+$', '', line)
        result_lines.append(line)
    return "\n".join(result_lines).strip()

# Expressions
def test_binop():
    assert py("x+y\n") == "x + y"

def test_number():
    assert py("42\n") == "42"

def test_string_plain():
    assert py('"hello"\n') == '"hello"'

def test_string_interpolated():
    # Transpiler emits f-string when interpolation markers present
    result = py('"hello $name$!"\n')
    assert result == 'f"hello {name}!"'

def test_string_escaped_dollar():
    result = py('"price: $$5"\n')
    assert result == '"price: $5"'

def test_zero_arg_call():
    assert py("foo!\n") == "foo()"

def test_method_zero_arg():
    assert py("msg.upper!\n") == "msg.upper()"

def test_pipeline():
    # Transpiler emits aliases (li, r) — prelude resolves them at runtime
    result = py("r(10)|li!\n")
    assert result == "li(r(10))"

def test_pipeline_three():
    # ma(lambda, source) wrapping; aliases preserved
    result = py("r(10)|ma(x->x*2)|li!\n")
    assert result == "li(ma(lambda x: x * 2, r(10)))"

def test_lambda():
    assert py("x->x*2\n") == "lambda x: x * 2"

def test_self_attr():
    assert py("@name\n") == "self.name"

def test_ternary():
    assert py("x if cond else y\n") == "x if cond else y"

# Statements
def test_assignment():
    assert py("x=42\n") == "x = 42"

def test_aug_assignment():
    assert py("x+=1\n") == "x += 1"

def test_append():
    assert py("items<<x\n") == "items.append(x)"

def test_ret():
    assert py("def f\n  return 42\n") == "def f():\n    return 42"

def test_function_implicit_return():
    result = py("def add x y\n  x+y\n")
    assert result == "def add(x, y):\n    return x + y"

def test_function_default_param():
    result = py("def greet name loud=0\n  name\n")
    assert "def greet(name, loud=0):" in result

def test_method():
    src = "class Dog\n  def @bark\n    p!\n"
    result = py(src)
    assert "def bark(self):" in result
    assert "p()" in result  # p is the prelude alias — transpiler emits p(), not print()

def test_class_inheritance():
    # Use a real L++ body — 'pass' is not an L++ keyword
    result = py("class GoldenRetriever:Dog\n  def @init name\n    @name=name\n")
    assert "class GoldenRetriever(Dog):" in result

def test_if_else():
    src = 'if x>5\n  p("big")\nelse\n  p("small")\n'
    result = py(src)
    assert "if x > 5:" in result
    assert "else:" in result

def test_elif():
    src = 'if x>5\n  p("big")\nelif x==5\n  p("mid")\nelse\n  p("small")\n'
    result = py(src)
    assert "elif x == 5:" in result

def test_for():
    # r is the prelude alias for range — transpiler emits r, not range
    result = py("for i in r(10)\n  p(i)\n")
    assert "for i in r(10):" in result
    assert "p(i)" in result

def test_for_tuple_unpack():
    result = py("for k,v in d.items!\n  p(k)\n")
    assert "for k, v in d.items():" in result

def test_do():
    result = py("while x>0\n  x-=1\n")
    assert "while x > 0:" in result

def test_try_err():
    src = "try\n  i(val)\nexcept ValueError e\n  p(e)\n"
    result = py(src)
    assert "try:" in result
    assert "except ValueError as e:" in result

def test_use_simple():
    result = py("use os\n")
    assert "import os" in result

def test_use_alias():
    result = py("use np=numpy\n")
    assert "import numpy as np" in result

def test_use_from():
    result = py("use pathlib:Path\n")
    assert "from pathlib import Path" in result

def test_use_from_alias():
    result = py("use pathlib:Path=P\n")
    assert "from pathlib import Path as P" in result

def test_alias_statement():
    result = py("alias sq=math.sqrt\n")
    assert "sq = math.sqrt" in result

def test_use_inside_function_indented():
    result = py("def f\n  use os\n  os\n")
    assert "    import os" in result

def test_use_multi_item_from():
    result = py("use pathlib:Path,PurePath\n")
    assert "from pathlib import Path" in result
    assert "from pathlib import PurePath" in result

def test_use_dotted():
    assert "import os.path" in py("use os.path\n")

def test_use_dotted_from():
    assert "from os.path import join" in py("use os.path:join\n")

def test_use_dotted_alias():
    assert "import os.path as p" in py("use p=os.path\n")

def test_use_dotted_from_alias():
    assert "from os.path import join as jn" in py("use os.path:join=jn\n")

def test_pipeline_kwargs():
    result = py("r(5)|so(reverse=1)\n")
    assert result == "so(r(5), reverse=1)"

def test_float_literal():
    assert py("1.0\n") == "1.0"

def test_compose():
    result = py("h=f&g\n")
    assert result == "h = (lambda *a, **kw: f(g(*a, **kw)))"

def test_compose_chain():
    result = py("h=f&g&k\n")
    assert result == "h = (lambda *a, **kw: (lambda *a, **kw: f(g(*a, **kw)))(k(*a, **kw)))"

def test_compose_in_lambda_body():
    result = py("x->f&g\n")
    assert result == "lambda x: (lambda *a, **kw: f(g(*a, **kw)))"

def test_string_with_double_quote():
    # L++ source: "say \"hi\""  →  Python: "say \"hi\""
    assert py('"say \\"hi\\""\n') == '"say \\"hi\\""'

def test_string_with_backslash():
    # L++ source: "path\\file"  →  Python: "path\\file"
    assert py('"path\\\\file"\n') == '"path\\\\file"'

def test_string_with_newline_escape():
    # L++ source: "line1\nline2"  →  Python: "line1\nline2"
    assert py('"line1\\nline2"\n') == '"line1\\nline2"'

def test_string_with_tab_escape():
    # L++ source: "col1\tcol2"  →  Python: "col1\tcol2"
    assert py('"col1\\tcol2"\n') == '"col1\\tcol2"'

def test_interpolated_string_with_double_quote():
    # L++ source: "$name$ said \"hi\""  →  Python: f"{name} said \"hi\""
    assert py('"$name$ said \\"hi\\""\n') == 'f"{name} said \\"hi\\""'

def test_interpolated_string_with_braces_and_escape():
    # L++ source: "result: {$val$} is \"ok\""
    # literal { and } become {{ and }} in the f-string;
    # \" becomes \" — both must survive in the correct order
    result = py('"result: {$val$} is \\"ok\\""\n')
    assert result == 'f"result: {{{val}}} is \\"ok\\""'

def test_break():
    result = py("for i in r(1)\n  break\n")
    assert "break" in result

def test_continue():
    result = py("for i in r(1)\n  continue\n")
    assert "continue" in result

def test_global():
    assert py("global x,y\n") == "global x, y"

def test_nonlocal():
    assert py("nl x\n") == "nonlocal x"

def test_raise_bare():
    assert py("raise\n") == "raise"

def test_raise_expr():
    result = py("raise ValueError(\"oops\")\n")
    assert "raise ValueError" in result

def test_raise_from():
    result = py("raise ValueError(\"oops\") from orig\n")
    assert "raise ValueError" in result
    assert "from orig" in result

def test_with():
    result = py("with open(\"f\") as fh\n  p(fh)\n")
    assert 'with open("f") as fh:' in result

def test_with_no_as():
    result = py("with lock!\n  p(\"ok\")\n")
    assert "with lock():" in result

def test_with_multi():
    result = py("with open(\"a\") as fa,open(\"b\") as fb\n  p(fa)\n")
    assert "as fa" in result
    assert "as fb" in result

def test_try_finally():
    src = "try\n  x=1\nexcept\n  x=2\nfinally\n  p(\"done\")\n"
    result = py(src)
    assert "finally:" in result
    assert 'p("done")' in result

def test_try_only_fin():
    src = "try\n  x=1\nfinally\n  p(\"done\")\n"
    result = py(src)
    assert "try:" in result
    assert "finally:" in result
    assert "except" not in result

def test_subscript_assign():
    assert py("d[k]=v\n") == "d[k] = v"

def test_attr_assign():
    assert py("obj.attr=v\n") == "obj.attr = v"

def test_unpack_assign():
    assert py("a,b=myfn!\n") == "a, b = myfn()"

def test_star_unpack():
    assert py("a,*b=lst\n") == "a, *b = lst"

def test_subscript_aug():
    assert py("d[k]+=1\n") == "d[k] += 1"

def test_attr_aug():
    assert py("obj.attr+=1\n") == "obj.attr += 1"

# Decorators
def test_decorator_simple_on_fn():
    result = py("@staticmethod\ndef foo x\n  x*2\n")
    assert result == "@staticmethod\ndef foo(x):\n    return x * 2"

def test_decorator_stacked():
    result = py("@classmethod\n@cache\ndef bar cls n\n  n\n")
    assert result == "@classmethod\n@cache\ndef bar(cls, n):\n    return n"

def test_decorator_call_expression():
    result = py("@lru_cache(maxsize=128)\ndef fib n\n  n\n")
    assert result == "@lru_cache(maxsize=128)\ndef fib(n):\n    return n"

def test_decorator_attribute_expression():
    result = py('@app.route("/")\ndef index\n  "hi"\n')
    assert result == '@app.route("/")\ndef index():\n    return "hi"'

def test_decorator_on_class():
    result = py("@dataclass\nclass Point\n  def @init x\n    @x=x\n")
    assert result == "@dataclass\nclass Point:\n    def __init__(self, x):\n        self.x = x"

def test_decorator_on_method():
    result = py("class Foo\n  @property\n  def @bar\n    @_bar\n")
    assert result == "class Foo:\n    @property\n    def bar(self):\n        return self._bar"

def test_no_decorator_unchanged():
    result = py("def foo x\n  x*2\n")
    assert result == "def foo(x):\n    return x * 2"

# multiple inheritance
def test_multi_inherit():
    result = py("class Foo:Bar,Baz\n  def @init\n    42\n")
    assert "class Foo(Bar, Baz):" in result

# for/else
def test_for_else():
    src = "for i in r(3)\n  p(i)\nelse\n  p(0)\n"
    result = py(src)
    assert "for i in r(3):" in result
    assert "else:" in result

# set literals
def test_set_literal():
    assert py("{1,2,3}\n") == "{1, 2, 3}"

def test_set_single():
    assert py("{42}\n") == "{42}"

# %= augmented assignment
def test_modulo_assign():
    assert py("x%=3\n") == "x %= 3"

# assert / del
def test_assert_basic():
    assert py("assert x==1\n") == "assert x == 1"

def test_assert_with_msg():
    assert py('assert x==1,"fail"\n') == 'assert x == 1, "fail"'

def test_del_basic():
    assert py("del x\n") == "del x"

def test_del_multi():
    assert py("del x,y\n") == "del x, y"

# slice notation
def test_slice_basic():
    assert py("lst[0:n]\n") == "lst[0:n]"

def test_slice_step():
    assert py("lst[::2]\n") == "lst[::2]"

def test_slice_open_end():
    assert py("lst[1:]\n") == "lst[1:]"

def test_slice_open_start():
    assert py("lst[:n]\n") == "lst[:n]"

def test_slice_full():
    assert py("lst[1:5:2]\n") == "lst[1:5:2]"

# *args / **kwargs
def test_star_args():
    result = py("def f *args\n  args\n")
    assert "def f(*args):" in result

def test_double_star_kwargs():
    result = py("def f **kwargs\n  kwargs\n")
    assert "def f(**kwargs):" in result

def test_mixed_params():
    result = py("def f x *args **kwargs\n  x\n")
    assert "def f(x, *args, **kwargs):" in result

# tuple literals / multi-value return
def test_return_tuple():
    result = py("def f\n  return a, b\n")
    assert "return a, b" in result

def test_assign_tuple_rhs():
    assert py("x=1,2,3\n") == "x = 1, 2, 3"

def test_tuple_expr_stmt():
    assert py("a,b\n") == "a, b"

def test_return_triple():
    result = py("def f\n  return x, y, z\n")
    assert "return x, y, z" in result

# list / dict comprehensions
def test_list_comp_basic():
    assert py("[x*x for x in r(n)]\n") == "[x * x for x in r(n)]"

def test_list_comp_with_if():
    assert py("[x for x in lst if x>0]\n") == "[x for x in lst if x > 0]"

def test_dict_comp_basic():
    assert py("{k: v for k,v in pairs}\n") == "{k: v for k, v in pairs}"

def test_dict_comp_with_if():
    assert py("{k: v for k,v in pairs if k>0}\n") == "{k: v for k, v in pairs if k > 0}"

def test_list_comp_in_assignment():
    assert py("sq=[x*x for x in r(5)]\n") == "sq = [x * x for x in r(5)]"

# ** and //
def test_power():
    assert py("a**b\n") == "a ** b"

def test_floordiv():
    assert py("a//b\n") == "a // b"

def test_power_precedence():
    assert py("a*b**c\n") == "a * b ** c"

# is / not in operators
def test_is_none():
    assert py("x is None\n") == "x is None"

def test_not_in():
    assert py("x not in col\n") == "x not in col"

def test_is_not_none():
    assert py("x is not None\n") == "x is not None"

def test_is_in_if():
    result = py("if x is None\n  x=1\n")
    assert "if x is None:" in result

def test_not_in_in_if():
    result = py("if x not in col\n  x=1\n")
    assert "if x not in col:" in result

# pass statement (item 18)
def test_pass_in_function_body():
    result = py("def f\n  pass\n")
    assert result == "def f():\n    pass"

def test_pass_in_except_body():
    src = "try\n  risky!\nexcept SomeError\n  pass\n"
    result = py(src)
    assert "except SomeError:" in result
    assert "pass" in result
    assert "return pass" not in result

def test_pass_in_if_body():
    src = "if cond\n  pass\nelse\n  p(\"no\")\n"
    result = py(src)
    assert "pass" in result
    assert "return pass" not in result

# multiple exception types per except (item 19)
def test_except_tuple_types():
    src = "try\n  x=1\nexcept (TypeError,ValueError) as e\n  p(e)\n"
    result = py(src)
    assert "except (TypeError, ValueError) as e:" in result

def test_except_tuple_types_no_binding():
    src = "try\n  x=1\nexcept (TypeError,ValueError)\n  p(\"err\")\n"
    result = py(src)
    assert "except (TypeError, ValueError):" in result

# set comprehensions (item 20)
def test_set_comp_basic():
    assert py("{x*2 for x in r(5)}\n") == "{x * 2 for x in r(5)}"

def test_set_comp_with_if():
    assert py("{x for x in lst if x>0}\n") == "{x for x in lst if x > 0}"

def test_set_comp_in_assignment():
    assert py("s={x*x for x in r(5)}\n") == "s = {x * x for x in r(5)}"

# chained comparisons (item 21)
def test_chained_lt():
    assert py("a < b < c\n") == "a < b < c"

def test_chained_mixed():
    assert py("0 <= x < n\n") == "0 <= x < n"

def test_chained_three_ops():
    assert py("a < b < c < d\n") == "a < b < c < d"

def test_single_comparison_unchanged():
    assert py("x < 5\n") == "x < 5"

def test_chained_in_if():
    result = py("if 0 <= x < n\n  p(x)\n")
    assert "if 0 <= x < n:" in result

# while/else (item 22)
def test_while_else():
    src = "while cond\n  p(1)\nelse\n  p(0)\n"
    result = py(src)
    assert "while cond:" in result
    assert "else:" in result
    assert "p(0)" in result

def test_while_no_else_unchanged():
    result = py("while x>0\n  x-=1\n")
    assert "while x > 0:" in result
    assert "else" not in result

# yield / generators (item 23)
def test_yield_value():
    result = py("def gen n\n  yield n\n")
    assert "yield n" in result
    assert "return yield" not in result

def test_yield_bare():
    result = py("def gen\n  yield\n")
    assert "yield" in result
    assert "return yield" not in result

def test_yield_from():
    result = py("def gen it\n  yield from it\n")
    assert "yield from it" in result
    assert "return yield" not in result

def test_yield_not_last():
    result = py("def gen n\n  yield n\n  yield n*2\n")
    assert result.count("yield") == 2
    assert "return yield" not in result

def test_yield_with_other_stmts():
    result = py("def countdown n\n  while n>0\n    yield n\n    n-=1\n")
    assert "yield n" in result
    assert "return yield" not in result

# lpp line markers (source map feature)
def test_lpp_marker_emitted():
    out = compile_lpp("x = 1\n")
    assert "  # lpp:1" in out

def test_lpp_markers_on_correct_lines():
    out = compile_lpp("x = 1\ny = 2\n")
    x_annotated = next(l for l in out.splitlines() if "x = 1" in l)
    y_annotated = next(l for l in out.splitlines() if "y = 2" in l)
    assert "  # lpp:1" in x_annotated
    assert "  # lpp:2" in y_annotated

def test_lpp_marker_on_compound_statement():
    out = compile_lpp("if True\n  x = 1\n")
    if_line = next(l for l in out.splitlines() if l.strip().startswith("if True"))
    assert "  # lpp:1" in if_line

def test_lpp_marker_on_decorated_fn():
    out = compile_lpp("@staticmethod\ndef foo x\n  x\n")
    dec_line = next(l for l in out.splitlines() if "@staticmethod" in l)
    assert "  # lpp:1" in dec_line

# Type annotations (item 24+)
def test_annotated_param():
    assert py("def f(x::int)\n    x\n") == "def f(x: int):\n    return x"

def test_return_annotation():
    assert py("def f()::bool\n    True\n") == "def f() -> bool:\n    return True"

def test_param_and_return_annotation():
    result = py("def f(x::int, y::str)::bool\n    True\n")
    assert result == "def f(x: int, y: str) -> bool:\n    return True"

def test_annotated_param_with_default():
    result = py("def f(x::int = 0)\n    x\n")
    assert result == "def f(x: int = 0):\n    return x"

def test_annotated_varargs():
    result = py("def f(*args::int)\n    args\n")
    assert result == "def f(*args: int):\n    return args"

def test_annotated_variable():
    assert py("x::int = 5\n") == "x: int = 5"

def test_bare_annotation():
    assert py("x::int\n") == "x: int"

def test_annotated_complex_type():
    assert py("items::list[str] = []\n") == "items: list[str] = []"

def test_annotated_dict_type():
    assert py("mapping::dict[str, int] = {}\n") == "mapping: dict[str, int] = {}"

def test_self_attr_annotated_assignment():
    result = py("def @init()\n    @name::str = \"hi\"\n")
    assert "self.name: str = \"hi\"" in result

def test_self_attr_bare_annotation():
    result = py("def @init()\n    @count::int\n")
    assert "self.count: int" in result
