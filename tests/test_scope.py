# tests/test_scope.py
from lpp.lexer import Lexer
from lpp.parser import Parser
from lpp.scope import resolve_scope


def _parse(source: str):
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


# Main source used by most tests.
# Line 1:  x = 1
# Line 2:  y = 2
# Line 3:  (blank)
# Line 4:  def add a b
# Line 5:      c = a + b
# Line 6:      return c
# Line 7:  (blank)
# Line 8:  def greet name
# Line 9:      msg = "hi"
# Line 10:     return msg
SOURCE = """\
x = 1
y = 2

def add a b
  c = a + b
  return c

def greet name
  msg = "hi"
  return msg
"""


def test_function_params_in_scope():
    tree = _parse(SOURCE)
    names = resolve_scope(tree, 5)
    assert "a" in names
    assert "b" in names


def test_local_assignment_in_scope():
    tree = _parse(SOURCE)
    names = resolve_scope(tree, 5)
    assert "c" in names


def test_correct_function_scope():
    tree = _parse(SOURCE)
    names = resolve_scope(tree, 9)
    assert "name" in names
    assert "msg" in names


def test_params_dont_bleed_across_functions():
    tree = _parse(SOURCE)
    names = resolve_scope(tree, 9)
    assert "a" not in names
    assert "b" not in names


def test_module_level_scope():
    tree = _parse(SOURCE)
    names = resolve_scope(tree, 1)
    assert "x" in names
    assert "y" in names
    assert "add" in names


def test_for_loop_variable_in_scope():
    source = """\
def process items
  for item in items
    print(item)
"""
    tree = _parse(source)
    # line 3 is inside the for body
    names = resolve_scope(tree, 3)
    assert "item" in names


def test_class_method_names_in_scope():
    source = """\
class Dog
  def bark self
    pass
  def fetch self
    pass
"""
    tree = _parse(source)
    # line 2 is inside the class body (bark method definition)
    names = resolve_scope(tree, 2)
    assert "bark" in names
    assert "fetch" in names
