# TextMate Grammar — Design Spec

**Date:** 2026-04-19  
**Status:** Approved

---

## Goal

Produce a single `syntaxes/lpp.tmLanguage.json` TextMate grammar that provides syntax highlighting for `.lpp` files in VS Code, Sublime Text, and (eventually) GitHub Linguist. No extension manifest or package files — just the grammar.

---

## File

```
syntaxes/lpp.tmLanguage.json
```

Root scope: `source.lpp`. File types: `["lpp"]`.

---

## Pattern Order

Rules are applied top-to-bottom, first-match wins. Order:

1. Comments
2. Strings (begin/end — contains sub-patterns)
3. Numbers
4. Language constants (`None`, `True`, `False`)
5. Storage type keywords (`def`, `class`)
6. Control flow keywords
7. Other keywords
8. Self-attributes (`@ident`)
9. Built-in functions (call-site lookahead)
10. L++ operators

---

## Token Categories

### 1. Comments

```
match:  #[^\n]*
name:   comment.line.number-sign.lpp
```

### 2. Strings with Interpolation

A `begin`/`end` rule bounded by `"`. Three nested sub-patterns fire inside the string body:

**2a. Escape sequences**
```
match:  \\[nt"\\]
name:   constant.character.escape.lpp
```

**2b. String interpolation block** — `$...$`
```
begin:  \$
end:    \$
name:   meta.interpolation.lpp

beginCaptures:
  0:  punctuation.definition.template-expression.begin.lpp

endCaptures:
  0:  punctuation.definition.template-expression.end.lpp

patterns:
  include: $self   (re-uses all root patterns so keywords/built-ins highlight inside $...$)
```

**2c. String body**
```
name:   string.quoted.double.lpp
```

### 3. Numbers

```
match:  \b\d+(\.\d+)?\b
name:   constant.numeric.lpp
```

Negative numbers: leading `-` is not matched here (it would cause false positives on binary minus). It falls through to the operator rule and displays as operator color adjacent to number color — visually acceptable.

### 4. Language Constants

```
match:  \b(None|True|False)\b
name:   constant.language.lpp
```

### 5. Storage Type Keywords

```
match:  \b(def|class)\b
name:   storage.type.lpp
```

### 6. Control Flow Keywords

```
match:  \b(if|elif|else|for|in|while|return|break|continue|try|except|finally|raise|with|yield)\b
name:   keyword.control.lpp
```

### 7. Other Keywords

```
match:  \b(use|alias|as|from|global|nl|is|not|assert|del|pass)\b
name:   keyword.other.lpp
```

### 8. Self-Attributes

```
match:  @[A-Za-z_]\w*
name:   variable.other.readwrite.instance.lpp
```

Covers `@x`, `@init`, `@__add__`, `@property`, `@staticmethod`, and decorators — `@` in L++ is always either a self-attr or a decorator, so a single scope is correct.

### 9. Built-in Functions

Only highlighted at call sites (followed by `(` or `!`) to avoid false positives on short names used as variables.

```
match:  \b(p|l|r|s|i|f|b|t|li|di|se|tu|en|zi|ma|fi|so|rv|su|mn|mx|ab|ro|an|al|nx|ip|op|rp|ga|sa|ha|od|ch|pw|hx|isa|sc)\b(?=\s*[(!])
name:   support.function.builtin.lpp
```

### 10. L++ Operators

```
match:  (->|<<|[|&!])
name:   keyword.operator.lpp
```

Covers `->` (lambda arrow), `<<` (append), `|` (pipeline), `&` (compose), `!` (no-arg call suffix).

Standard arithmetic and comparison operators (`+`, `-`, `*`, `/`, `=`, `==`, `<`, etc.) are left unhighlighted — they default to the editor's base text color, which is conventional for most language grammars.

---

## What Is NOT Highlighted

- Arithmetic/comparison operators (`+`, `-`, `*`, `/`, `=`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `+=`, etc.) — conventional to leave as base text
- Delimiters (`(`, `)`, `[`, `]`, `{`, `}`, `,`, `.`) — conventional
- Negative number leading `-` — falls through to operator rule (acceptable)
- Type annotation candidate syntax (`::`) — not yet implemented in L++

---

## Testing

Manual verification in VS Code using "Developer: Inspect Editor Tokens and Scopes" (`Ctrl+Shift+P`) on `examples/showcase.lpp` and `examples/fizzbuzz.lpp`. Check:

- [ ] Comments gray out
- [ ] String body highlighted; `$...$` delimiters distinct; keywords inside interpolation highlighted
- [ ] `def` / `class` colored as storage types
- [ ] Control keywords colored distinctly from other keywords
- [ ] `@x`, `@init` colored as instance variables
- [ ] `p("hi")`, `li!`, `ma(f)` colored as built-ins; `i = 5` is NOT
- [ ] `|`, `->`, `!`, `&`, `<<` colored as operators

---

## What Does Not Change

- No Python source files touched
- No existing test suite impact
- No `package.json` or extension manifest created
