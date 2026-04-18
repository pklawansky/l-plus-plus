# l++

A terse Python transpiler designed to minimize token count without sacrificing expressiveness. Write compact `.lpp` source files; the compiler emits idiomatic Python.

The primary use case is authoring Python logic in contexts where tokens are expensive — LLM prompts, code-heavy chat turns, embedded snippets — while keeping the code fully executable.

---

## Why l++

Python is readable but verbose. `l++` strips the ceremony:

| Python | l++ |
|--------|-----|
| `def greet(name):` | `def greet name` |
| `print(len(items))` | `p(l(items))` |
| `return x * 2` | `return x*2` (or just `x*2` as the last line) |
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

### Single file

```sh
# Print transpiled Python to stdout
lpp program.lpp

# Write to a file
lpp program.lpp -o program.py

# Run immediately
lpp program.lpp --run

# Validate only (exit 0 = clean, exit 1 = errors) — useful for CI
lpp program.lpp --check
```

### Directory

```sh
# Compile all .lpp files under src/ into out/ (mirrors directory structure)
lpp src/ -o out/

# Validate all .lpp files in a directory
lpp src/ --check
```

### Watch mode

Recompiles on every file save. Uses stdlib polling — no extra dependencies. `-o` is required.

```sh
lpp watch src/ -o out/
lpp watch program.lpp -o .

# Custom poll interval (default: 0.5s)
lpp watch src/ -o out/ --interval 1.0
```

### Version

```sh
lpp --version
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
  elif i%3==0
    p("Fizz")
  elif i%5==0
    p("Buzz")
  else
    p(i)
```

Run it:
```sh
lpp fizzbuzz.lpp --run
```

---

## Language Reference

### Keywords

Standard Python control-flow keywords are used as-is. The only l++-specific keywords are those that provide genuine syntactic compression beyond a single-token swap.

| l++ | Python | Notes |
|-----|--------|-------|
| `def name params` | `def name(params):` | No parentheses on params |
| `def @name params` | method definition | `self` injected automatically |
| `class Name` | `class Name:` | |
| `class Name:Base` | `class Name(Base):` | |
| `if expr` | `if expr:` | No colon |
| `elif expr` | `elif expr:` | No colon |
| `else` | `else:` | No colon |
| `for x in expr` | `for x in expr:` | No colon |
| `for x,y in expr` | `for x, y in expr:` | Tuple unpacking |
| `while expr` | `while expr:` | No colon |
| `return expr` | `return expr` | |
| `return` | `return` | |
| `try` | `try:` | |
| `except ExcType name` | `except ExcType as name:` | |
| `except ExcType` | `except ExcType:` | |
| `except` | `except:` | |
| `finally` | `finally:` | |
| `use module` | `import module` | Unified import syntax |
| `use alias=module` | `import module as alias` | |
| `use module:item` | `from module import item` | |
| `use module:item=alias` | `from module import item as alias` | |
| `use module:a,b,c` | `from module import a, b, c` | |
| `alias name = expr` | `name = expr` | Assigns any callable |
| `raise ExcType(msg)` | `raise ExcType(msg)` | |
| `raise exc from cause` | `raise exc from cause` | |
| `with expr as name` | `with expr as name:` | |
| `global x, y` | `global x, y` | |
| `nl x, y` | `nonlocal x, y` | `nl` kept — `nonlocal` is 2 tokens |
| `break` | `break` | |
| `continue` | `continue` | |

Blocks are delimited by **indentation** — no colons, no braces.

### Implicit Return

The last expression in a function body is automatically returned:

```
def double x
  x * 2
```

Compiles to:
```python
def double(x):
    return x * 2
```

Use an explicit `return` anywhere else in the body.

### Self and Methods

Inside a `class` block, prefix method definitions with `@`:

```
class Counter
  def @init start=0
    @count = start

  def @inc
    @count += 1

  def @value
    @count
```

- `def @init` → `def __init__(self, ...)` (dunder names handled automatically)
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
result = "yes" if cond else "no"
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
def flatten lst
  result = []
  for item in lst
    if isa(item, li)
      result << flatten(item)
    else
      result << item
  result

def main
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
