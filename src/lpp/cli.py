import sys
import argparse
from .lexer import LexError
from .parser import ParseError
from . import compile_lpp, __version__


def _format_error(label: str, err: Exception, source: str) -> str:
    line = getattr(err, "line", None)
    col = getattr(err, "col", None)
    loc = f" at line {line}" if line else ""
    if col is not None:
        loc += f", col {col}"
    lines = [f"lpp: {label}{loc}: {err}"]
    if line and source:
        src_lines = source.splitlines()
        if 0 < line <= len(src_lines):
            lines.append(f"  {src_lines[line - 1]}")
            if col is not None:
                lines.append(f"  {' ' * (col - 1)}^")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lpp",
        description="L++ transpiler — compile .lpp files to Python",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"lpp {__version__}"
    )
    parser.add_argument("file", help=".lpp source file")
    parser.add_argument("-o", "--output", help="write Python output to file instead of stdout")
    parser.add_argument("--run", action="store_true", help="execute transpiled Python immediately")
    parser.add_argument("--check", action="store_true",
                        help="validate only — parse without emitting output (exits 1 on error)")
    args = parser.parse_args()

    try:
        with open(args.file) as f:
            source = f.read()
    except FileNotFoundError:
        print(f"lpp: error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        python_src = compile_lpp(source)
    except (LexError, ParseError) as e:
        print(_format_error("error", e, source), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"lpp: internal error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        pass  # compiled successfully, nothing to emit
    elif args.run:
        exec(compile(python_src, args.file, "exec"), {"__name__": "__main__"})
    elif args.output:
        with open(args.output, "w") as f:
            f.write(python_src)
        print(f"Written to {args.output}")
    else:
        print(python_src)


if __name__ == "__main__":
    main()
