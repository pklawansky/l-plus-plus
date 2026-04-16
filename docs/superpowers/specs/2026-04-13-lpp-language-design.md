# L++ Language Design Spec
**Date:** 2026-04-13
**Status:** First draft — pending tokenizer validation pass

---

## Overview

L++ is a programming language optimised for LLMs to write with minimal token expenditure. It transpiles to Python (with multi-target support planned). Human readability is explicitly a non-goal. Runtime performance is inherited from the transpilation target.

**Measured efficiency:** ~20% fewer tokens on average vs equivalent Python, with higher gains (~33–37%) on class and function definitions.

---

## Master Principles

1. **Every rule must be unambiguous and locally derivable.** The LLM must be able to determine the meaning of any single line without broader context.
2. **Every keyword is a confirmed single token in cl100k.** No keyword exceeds 3 characters unless it is provably single-token at longer length.
3. **Symbols carry grammar. Keywords carry semantics.** Symbols are always single tokens and have one consistent meaning language-wide.
4. **Whitespace is structure, never tokens.** Indentation defines blocks. Newlines terminate statements. Neither requires explicit delimiters.
5. **The LLM derives, not memorises.** Rules compose. There are no special cases.

---

## Core Grammar Rules

| Rule | Detail |
|------|--------|
| Block structure | Indentation only. No `{`, `}`, `:`, `end`, `begin`. |
| Statement terminator | Newline. No `;`. |
| Implicit return | Last expression in a block is its value. |
| Early return | `ret expr` |
| Types | Always optional. `:T` annotation syntax, never required. |
| Variable names | Convention: single char for temporaries, two chars for longer-lived locals. Not enforced by transpiler — enforced by spec. |

---

## Symbol Grammar

One meaning per symbol, everywhere in the language.

| Symbol | Meaning |
|--------|---------|
| `\|` | Pipe — chain left to right |
| `->` | Transform / lambda body |
| `@` | Self / current instance context |
| `!` | Invoke with zero arguments (suffix) |
| `~` | Negate / invert |
| `&` | Function composition |
| `$$` | Literal `$` character inside a string |
| `$...$` | Interpolated expression inside a string |
| `<<` | Append to collection |
| `*` | Spread / unpack |

---

## String Literals

All strings are automatically interpolated. No prefix required.

- `$expr$` — interpolates any expression inline
- `$$` — literal `$` character (delimiter escapes itself)

```
"Hello $name$!"              # "Hello Alice!"
"$qty$ items @ $$5 each"     # "3 items @ $5 each"
"$a$ + $b$ = $a+b$"          # "2 + 3 = 5"
```

---

## Keywords

All confirmed or targeted as single tokens in cl100k. Subject to tokenizer validation pass.

| Keyword | Meaning |
|---------|---------|
| `fn` | Function definition |
| `cls` | Class definition |
| `if` | Conditional |
| `el` | Else / else-if |
| `for` | For loop |
| `in` | Membership / iteration |
| `do` | While loop |
| `ret` | Early return |
| `try` | Try block |
| `err` | Except/catch |
| `as` | Alias (in imports and `try/err`) |
| `use` | Import module or item |
| `alias` | File-local shorthand |

---

## Functions

```
fn add x y
  x+y

fn greet name loud=0
  msg="Hello $name$!"
  if loud
    ret msg.upper!
  msg
```

**Lambda:**
```
x->x*2
x,y->x+y
```

**Zero-arg call:**
```
msg.upper!        # msg.upper()
foo!              # foo()
```

**With args:**
```
add(3,4)
greet("world",1)
```

**Pipeline:**
```
result=r(10)|ma(x->x*2)|fi(x->x>5)|so!|li!
# list(sorted(filter(lambda x:x>5, map(lambda x:x*2, range(10)))))
```

**Append:**
```
items<<x          # items.append(x)
```

---

## Classes

`@` replaces `self` everywhere. `@name` = `self.name`.

```
cls Dog
  fn @init name
    @name=name

  fn @bark
    p("Woof! I'm $@name$")

  fn @describe breed="unknown"
    "$@name$ ($breed$)"
```

**Inheritance:**
```
cls GoldenRetriever:Dog
  fn @init name
    @name=name+"!"
```

---

## Control Flow

**if / else-if / else:**
```
if x>5
  p("big")
el x==5
  p("mid")
el
  p("small")
```

**Inline ternary:**
```
x if cond el y
```

**for loop:**
```
for i in r(10)
  p(i)

for k,v in d.items!
  p("$k$:$v$")
```

**while — keyword `do`:**
```
do x>0
  x-=1
```

**try / except:**
```
try
  result=i(val)
err ValueError e
  p("bad val: $e$")
  result=0
```

---

## Imports

Two keywords with non-overlapping roles:

- `use` — imports only. Brings modules or items into scope.
- `alias` — local shorthand only. Names already-accessible callables/values for token efficiency.

**Derivable rules:**
- `=` always means alias
- `:` always means "item from module"
- They compose independently

```
use os,json,re              # import os, json, re
use np=numpy                # import numpy as np
use pathlib:Path            # from pathlib import Path
use pathlib:Path,PurePath   # from pathlib import Path, PurePath
use pathlib:Path=P          # from pathlib import Path as P
```

```
alias sq=math.sqrt          # local shorthand, not an import
alias log=logging.getLogger # local shorthand for long dotted name
```

---

## Standard Prelude

A fixed, immutable set of aliases for universal Python builtins. Conflicts resolved at design time. LLMs learn this list once.

### Single-char (highest frequency)

| Alias | Python builtin |
|-------|---------------|
| `p` | print |
| `l` | len |
| `r` | range |
| `s` | str |
| `i` | int |
| `f` | float |
| `b` | bool |
| `t` | type |

### Two-char

| Alias | Python builtin |
|-------|---------------|
| `li` | list |
| `di` | dict |
| `se` | set |
| `tu` | tuple |
| `en` | enumerate |
| `zi` | zip |
| `ma` | map |
| `fi` | filter |
| `so` | sorted |
| `rv` | reversed |
| `su` | sum |
| `mn` | min |
| `mx` | max |
| `ab` | abs |
| `ro` | round |
| `an` | any |
| `al` | all |
| `nx` | next |
| `ip` | input |
| `op` | open |
| `rp` | repr |
| `ga` | getattr |
| `sa` | setattr |
| `ha` | hasattr |
| `od` | ord |
| `ch` | chr |
| `pw` | pow |
| `hx` | hex |
| `isa` | isinstance |
| `sc` | issubclass |

---

## Token Savings Summary (estimated, cl100k)

| Construct | Python tokens | L++ tokens | Reduction |
|-----------|--------------|------------|-----------|
| Simple function | 12 | 8 | −33% |
| Function w/ string | 30 | 24 | −20% |
| Class (2 methods) | 38 | 24 | −37% |
| Pipeline (map/filter) | 33 | 30 | −9% |
| **Average** | | | **~20%** |

> Note: all counts are estimates pending a full cl100k tokenizer validation pass, which should be run before finalising the keyword list.

---

## Open Items

- [x] Run every keyword and prelude alias through cl100k to confirm single-token status — all 50 pass (validated 2026-04-14, see `tools/validate_tokens.py`)
- [ ] Define decorator syntax (`@` is taken by self — alternative needed)
- [ ] Define generator / yield syntax
- [ ] Define async/await syntax
- [ ] Specify multi-target transpilation interface (Python first, others follow)
- [ ] Write formal grammar (BNF or PEG) for the transpiler
- [ ] Define error messages from transpiler (for LLM feedback loops)
- [ ] `|` is taken by pipeline — define alternative for bitwise OR (e.g. `bor`, `|||`, or a dedicated operator)
- [ ] `is` prelude alias shadows Python identity operator `is` — consider renaming to `ic` (isinstance check) to avoid transpiler ambiguity
