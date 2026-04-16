# tests/test_transpiler.py
import pytest
from lpp import compile_lpp

def py(src: str) -> str:
    """Compile L++ and strip prelude for test clarity."""
    full = compile_lpp(src)
    # Strip prelude lines (up to first blank line after prelude)
    lines = full.split("\n")
    start = next(i for i, l in enumerate(lines) if l == "") + 1
    return "\n".join(lines[start:]).strip()

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
