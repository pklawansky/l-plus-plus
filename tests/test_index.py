# tests/test_index.py
from lpp.index import WorkspaceIndex

# Valid L++ syntax (indentation-based, no parens/colons in def/class headers)
SOURCE = """\
def add a b
  return a + b

class Vec2
  def init self
    pass

x = 10
y = 20
"""

def test_indexes_functions():
    idx = WorkspaceIndex()
    idx.index_file("file:///foo.lpp", SOURCE)
    syms = idx.find("add")
    assert len(syms) == 1
    assert syms[0].kind == "function"
    assert syms[0].line == 1

def test_indexes_classes():
    idx = WorkspaceIndex()
    idx.index_file("file:///foo.lpp", SOURCE)
    syms = idx.find("Vec2")
    assert len(syms) == 1
    assert syms[0].kind == "class"

def test_indexes_top_level_variables():
    idx = WorkspaceIndex()
    idx.index_file("file:///foo.lpp", SOURCE)
    syms = idx.find("x")
    assert len(syms) == 1
    assert syms[0].kind == "variable"

def test_nested_methods_not_indexed():
    idx = WorkspaceIndex()
    idx.index_file("file:///foo.lpp", SOURCE)
    assert idx.find("init") == []

def test_parse_error_keeps_old_entry():
    idx = WorkspaceIndex()
    idx.index_file("file:///foo.lpp", SOURCE)
    idx.index_file("file:///foo.lpp", "def\n")  # broken — no function name
    assert idx.find("add") != []

def test_all_symbols_returns_all():
    idx = WorkspaceIndex()
    idx.index_file("file:///foo.lpp", SOURCE)
    names = {s.name for s in idx.all_symbols()}
    assert {"add", "Vec2", "x", "y"} <= names

def test_cross_file_symbols():
    idx = WorkspaceIndex()
    idx.index_file("file:///a.lpp", "def foo\n  pass\n")
    idx.index_file("file:///b.lpp", "def bar\n  pass\n")
    names = {s.name for s in idx.all_symbols()}
    assert "foo" in names and "bar" in names

def test_symbol_uri():
    idx = WorkspaceIndex()
    idx.index_file("file:///a.lpp", "def foo\n  pass\n")
    syms = idx.find("foo")
    assert syms[0].uri == "file:///a.lpp"
