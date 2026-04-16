# l++

A terse Python transpiler designed to minimize token count without sacrificing expressiveness. Write compact `.lpp` source files; the compiler emits idiomatic Python.

The primary use case is authoring Python logic in contexts where tokens are expensive — LLM prompts, code-heavy chat turns, embedded snippets — while keeping the code fully executable.

---

## Why l++

Python is readable but verbose. `l++` strips the ceremony:

| Python | l++ |
|--------|-----|
| `def greet(name):` | `fn greet name` |
| `print(len(items))` | `p(l(items))` |
| `return x * 2` | `ret x*2` (or just `x*2` as the last line) |
| `for i in range(10):` | `for i in r(10)` |
| `[x*2 for x in items]` | `items\|ma(x->x*2)\|li!` |
| `lambda x, y: x + y` | `x,y -> x+y` |

---

## Installation

Requires Python 3.11+.

**From source (editable install):**

```sh
pip install -e .
```

**With uv:**

```sh
uv pip install -e .
```

This installs the `lpp` CLI entry point.

---

## CLI Usage

```sh
# Print transpiled Python to stdout
lpp program.lpp

# Run immediately
lpp program.lpp --run

# Write Python output to a file
lpp program.lpp -o program.py
```

Errors include a source location and caret:

```
lpp: error at line 3, col 5: unterminated string literal
  p("hello
      ^
```

---

## Quick Example

**fizzbuzz.lpp**
```
for i in r(1,101)
  if i%15==0
    p("FizzBuzz")
  el i%3==0
    p("Fizz")
  el i%5==0
    p("Buzz")
  el
    p(i)
```

Run it:
```sh
lpp fizzbuzz.lpp --run
```

---

## Language Reference

### Keywords

| l++ | Python | Notes |
|-----|--------|-------|
| `fn name params` | `def name(params):` | No parentheses on params |
| `fn @name params` | method definition | `self` injected automatically |
| `cls Name` | `class Name:` | |
| `cls Name:Base` | `class Name(Base):` | |
| `if expr` | `if expr:` | No colon |
| `el expr` | `elif expr:` | |
| `el` | `else:` | Bare `el` = else |
| `for x in expr` | `for x in expr:` | |
| `for x,y in expr` | `for x, y in expr:` | Tuple unpacking |
| `do expr` | `while expr:` | |
| `ret expr` | `return expr` | |
| `ret` | `return` | |
| `try` | `try:` | |
| `err ExcType name` | `except ExcType as name:` | |
| `err ExcType` | `except ExcType:` | |
| `err` | `except:` | |
| `fin` | `finally:` | |
| `use module` | `import module` | |
| `use alias=module` | `import module as alias` | |
| `use module:item` | `from module import item` | |
| `use module:item=alias` | `from module import item as alias` | |
| `use module:a,b,c` | `from module import a, b, c` | |
| `alias name = expr` | `name = expr` (function alias) | Assigns any callable |
| `raise ExcType(msg)` | `raise ExcType(msg)` | |
| `raise exc from cause` | `raise exc from cause` | |
| `with expr as name` | `with expr as name:` | |
| `global x, y` | `global x, y` | |
| `nl x, y` | `nonlocal x, y` | |
| `break` | `break` | |
| `continue` | `continue` | |

Blocks are delimited by **indentation** — no colons, no braces.

### Implicit Return

The last expression in a function body is automatically returned:

```
fn double x
  x * 2
```

Compiles to:
```python
def double(x):
    return x * 2
```

Use an explicit `ret` anywhere else in the body.

### Self and Methods

Inside a `cls` block, prefix method definitions with `@`:

```
cls Counter
  fn @init start=0
    @count = start

  fn @inc
    @count += 1

  fn @value
    @count
```

- `fn @init` → `def __init__(self, ...)` (dunder names handled automatically)
- `@count` → `self.count`

### Operators

| l++ | Meaning |
|-----|---------|
| `x \| f` | Pipeline: pass `x` into `f` |
| `x -> expr` | Lambda: `lambda x: expr` |
| `x,y -> expr` | Multi-param lambda |
| `f & g` | Compose: `lambda *a, **kw: f(g(*a, **kw))` |
| `~expr` | Logical not |
| `expr!` | Zero-argument call: `expr()` |
| `lst << val` | `lst.append(val)` |
| `@attr` | `self.attr` |

### Pipeline

Chain operations left-to-right. The accumulated value is inserted as the **last positional argument** before any keyword arguments:

```
r(10) | ma(x->x*2) | fi(x->x>5) | li!
```

Compiles to:
```python
li(fi(lambda x: x > 5, ma(lambda x: x * 2, r(10))))
```

With keyword arguments:
```
items | so(reverse=1) | li!
```

Compiles to:
```python
li(so(items, reverse=1))
```

### String Interpolation

Use `$expr$` inside double-quoted strings:

```
name = "world"
p("hello $name$!")
p("2 + 2 = $2+2$")
```

Compiles to f-strings. Escape a literal `$` with `$$`.

### Ternary Expression

```
result = "yes" if cond el "no"
```

Compiles to:
```python
result = "yes" if cond else "no"
```

### Unpack Assignment

```
a, b, *rest = items
```

Works as in Python. Use `*name` for the rest target.

---

## Prelude

These aliases are injected at the top of every compiled file — no imports needed.

| l++ | Python |
|-----|--------|
| `p` | `print` |
| `l` | `len` |
| `r` | `range` |
| `s` | `str` |
| `i` | `int` |
| `f` | `float` |
| `b` | `bool` |
| `t` | `type` |
| `li` | `list` |
| `di` | `dict` |
| `se` | `set` |
| `tu` | `tuple` |
| `en` | `enumerate` |
| `zi` | `zip` |
| `ma` | `map` |
| `fi` | `filter` |
| `so` | `sorted` |
| `rv` | `reversed` |
| `su` | `sum` |
| `mn` | `min` |
| `mx` | `max` |
| `ab` | `abs` |
| `ro` | `round` |
| `an` | `any` |
| `al` | `all` |
| `nx` | `next` |
| `ip` | `input` |
| `op` | `open` |
| `rp` | `repr` |
| `ga` | `getattr` |
| `sa` | `setattr` |
| `ha` | `hasattr` |
| `od` | `ord` |
| `ch` | `chr` |
| `pw` | `pow` |
| `hx` | `hex` |
| `isa` | `isinstance` |
| `sc` | `issubclass` |

---

## Larger Example

```
fn flatten lst
  result = []
  for item in lst
    if isa(item, li)
      result << flatten(item)
    el
      result << item
  result

fn main
  data = [[1,2,[3]],4,[5,6]]
  flat = flatten(data)
  p("flat: $flat$")
  total = flat|su
  p("sum: $total$")

main()
```

---

## Project Structure

```
src/lpp/
  __init__.py      # compile_lpp(source) → python_src
  tokens.py        # TokenType enum and KEYWORDS map
  lexer.py         # Tokenizer with indent/dedent tracking
  parser.py        # Recursive-descent parser → AST
  ast_nodes.py     # AST node dataclasses
  transpiler.py    # AST → Python source
  prelude.py       # Prelude alias table and injector
  cli.py           # lpp CLI entry point
examples/
  fizzbuzz.lpp
tests/
  test_lexer.py
  test_parser.py
  test_transpiler.py
  test_integration.py
  test_prelude.py
```

---

## Running Tests

```sh
pytest
```
