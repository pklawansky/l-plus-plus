import subprocess, sys, textwrap, tempfile, os
from lpp import compile_lpp

def run_lpp(src: str) -> str:
    """Compile L++ and execute it, return stdout."""
    python_src = compile_lpp(src)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(python_src)
        path = f.name
    try:
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        return result.stdout.strip()
    finally:
        os.unlink(path)

def test_hello_world():
    assert run_lpp('p("hello world")\n') == "hello world"

def test_function_call():
    src = textwrap.dedent("""\
        def add x y
          x+y
        p(add(3,4))
    """)
    assert run_lpp(src) == "7"

def test_string_interpolation():
    src = 'name="world"\np("hello $name$!")\n'
    assert run_lpp(src) == "hello world!"

def test_for_loop():
    src = textwrap.dedent("""\
        acc=[]
        for i in r(3)
          acc<<i
        p(acc)
    """)
    assert run_lpp(src) == "[0, 1, 2]"

def test_pipeline():
    src = "p(r(5)|ma(x->x*2)|li!)\n"
    assert run_lpp(src) == "[0, 2, 4, 6, 8]"

def test_class():
    src = textwrap.dedent("""\
        class Dog
          def @init name
            @name=name
          def @bark
            p("Woof! I'm $@name$")
        d=Dog("Rex")
        d.bark!
    """)
    assert run_lpp(src) == "Woof! I'm Rex"

def test_string_escape_roundtrip():
    # Escaped characters must survive the full lex → parse → transpile → exec pipeline
    src = 'p("say \\"hi\\"\\nline2")\n'
    assert run_lpp(src) == 'say "hi"\nline2'

def test_function_composition():
    src = textwrap.dedent("""\
        def double x
          x*2
        def inc x
          x+1
        h=double&inc
        p(h(4))
    """)
    assert run_lpp(src) == "10"

def test_break_exits_loop():
    src = textwrap.dedent("""\
        acc=[]
        for i in r(10)
          if i==3
            break
          acc<<i
        p(acc)
    """)
    assert run_lpp(src) == "[0, 1, 2]"

def test_raise_caught():
    src = textwrap.dedent("""\
        try
          raise ValueError("oops")
        except ValueError e
          p("caught")
    """)
    assert run_lpp(src) == "caught"

def test_with_file():
    src = textwrap.dedent("""\
        use os
        path="test_with_tmp.txt"
        with open(path,"w") as fh
          fh.write("hello")
        with open(path) as r
          content=r.read!
        os.unlink(path)
        p(content)
    """)
    assert run_lpp(src) == "hello"

def test_global_mutation():
    src = textwrap.dedent("""\
        x=0
        def bump
          global x
          x+=1
        bump!
        bump!
        p(x)
    """)
    assert run_lpp(src) == "2"

def test_finally_runs():
    src = textwrap.dedent("""\
        log=[]
        try
          log<<1
          raise RuntimeError("e")
        except
          log<<2
        finally
          log<<3
        p(log)
    """)
    assert run_lpp(src) == "[1, 2, 3]"

def test_unpack_roundtrip():
    src = textwrap.dedent("""\
        a,b=[1,2]
        p(a)
        p(b)
    """)
    assert run_lpp(src) == "1\n2"

def test_staticmethod_decorator():
    src = textwrap.dedent("""\
        class MathUtils
          @staticmethod
          def add x y
            x+y
        p(MathUtils.add(3,4))
    """)
    assert run_lpp(src) == "7"

def test_property_decorator():
    src = textwrap.dedent("""\
        class Circle
          def @init r
            @r=r
          @property
          def @area
            3.14159*@r*@r
        c=Circle(5)
        p(round(c.area,2))
    """)
    assert run_lpp(src) == "78.54"

def test_class_decorator():
    src = textwrap.dedent("""\
        use dataclasses:dataclass
        @dataclass
        class Point
          def @init x y
            @x=x
            @y=y
        pt=Point(1,2)
        p(pt.x+pt.y)
    """)
    assert run_lpp(src) == "3"
