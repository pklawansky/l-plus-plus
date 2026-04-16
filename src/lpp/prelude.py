# src/lpp/prelude.py

PRELUDE: dict[str, str] = {
    # Single-char
    "p":  "print",
    "l":  "len",
    "r":  "range",
    "s":  "str",
    "i":  "int",
    "f":  "float",
    "b":  "bool",
    "t":  "type",
    # Two-char
    "li": "list",
    "di": "dict",
    "se": "set",
    "tu": "tuple",
    "en": "enumerate",
    "zi": "zip",
    "ma": "map",
    "fi": "filter",
    "so": "sorted",
    "rv": "reversed",
    "su": "sum",
    "mn": "min",
    "mx": "max",
    "ab": "abs",
    "ro": "round",
    "an": "any",
    "al": "all",
    "nx": "next",
    "ip": "input",
    "op": "open",
    "rp": "repr",
    "ga": "getattr",
    "sa": "setattr",
    "ha": "hasattr",
    "od": "ord",
    "ch": "chr",
    "pw": "pow",
    "hx": "hex",
    "isa": "isinstance",  # 'isa' not 'is' — 'is' is a Python keyword, emitting it causes SyntaxError
    "sc": "issubclass",
}

def inject_prelude(python_src: str) -> str:
    lines = ["# L++ prelude"]
    for alias, target in PRELUDE.items():
        lines.append(f"{alias} = {target}")
    lines.append("")
    return "\n".join(lines) + "\n" + python_src
