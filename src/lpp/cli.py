import sys
import os
import argparse
import time
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


def _walk_lpp_files(src_dir: str):
    """Yield absolute paths of all .lpp files under src_dir."""
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if fname.endswith(".lpp"):
                yield os.path.join(root, fname)


def _check_dir(src_dir: str) -> bool:
    """Parse-only check of all .lpp files under src_dir. Returns True if clean."""
    clean = True
    for src_path in _walk_lpp_files(src_dir):
        source = ""
        try:
            with open(src_path) as f:
                source = f.read()
            compile_lpp(source)
        except (LexError, ParseError) as e:
            print(_format_error(f"error in {src_path}", e, source), file=sys.stderr)
            clean = False
        except Exception as e:
            print(f"lpp: internal error in {src_path}: {e}", file=sys.stderr)
            clean = False
    return clean


def _compile_dir(src_dir: str, out_dir: str) -> bool:
    """Compile all .lpp files under src_dir into out_dir. Returns True if clean."""
    clean = True
    for src_path in _walk_lpp_files(src_dir):
        rel = os.path.relpath(src_path, src_dir)
        out_path = os.path.join(out_dir, os.path.splitext(rel)[0] + ".py")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        source = ""
        try:
            with open(src_path) as f:
                source = f.read()
            python_src = compile_lpp(source)
            with open(out_path, "w") as f:
                f.write(python_src)
        except (LexError, ParseError) as e:
            print(_format_error(f"error in {src_path}", e, source), file=sys.stderr)
            clean = False
        except Exception as e:
            print(f"lpp: internal error in {src_path}: {e}", file=sys.stderr)
            clean = False
    return clean


def _watch(src: str, out_dir: str, interval: float) -> None:
    """Poll src for mtime changes and recompile .lpp files on modification."""
    def snapshot():
        if os.path.isfile(src):
            return {src: os.path.getmtime(src)}
        return {p: os.path.getmtime(p) for p in _walk_lpp_files(src)}

    def compile_one(src_path: str) -> None:
        rel = os.path.relpath(src_path, src) if os.path.isdir(src) else os.path.basename(src_path)
        out_path = os.path.join(out_dir, os.path.splitext(rel)[0] + ".py")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        source = ""
        try:
            with open(src_path) as f:
                source = f.read()
            python_src = compile_lpp(source)
            with open(out_path, "w") as f:
                f.write(python_src)
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] compiled {src_path} -> {out_path}")
        except (LexError, ParseError) as e:
            print(_format_error(f"error in {src_path}", e, source), file=sys.stderr)
        except Exception as e:
            print(f"lpp: internal error in {src_path}: {e}", file=sys.stderr)

    os.makedirs(out_dir, exist_ok=True)
    prev: dict = {}
    print(f"lpp watch: watching {src} -> {out_dir}  (Ctrl-C to stop)")
    try:
        while True:
            curr = snapshot()
            for path, mtime in curr.items():
                if prev.get(path) != mtime:
                    compile_one(path)
            prev = curr
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nlpp watch: stopped")


def main() -> None:
    # Fast-path: detect 'watch' subcommand before argparse sees the positionals.
    # Using parse_known_args with subparsers would reject file paths as invalid
    # subcommand choices, so we inspect argv directly.
    argv = sys.argv[1:]

    if argv and argv[0] == "--version":
        print(f"lpp {__version__}")
        return

    if argv and argv[0] == "watch":
        watch_p = argparse.ArgumentParser(prog="lpp watch",
                                          description="watch files and recompile on change")
        watch_p.add_argument("file", help=".lpp source file or directory to watch")
        watch_p.add_argument("-o", "--output", required=True, help="output directory")
        watch_p.add_argument("--interval", type=float, default=0.5,
                             help="poll interval in seconds (default: 0.5)")
        wargs = watch_p.parse_args(argv[1:])
        _watch(wargs.file, wargs.output, wargs.interval)
        return

    # Compile path
    compile_p = argparse.ArgumentParser(
        prog="lpp",
        description="L++ transpiler — compile .lpp files to Python",
    )
    compile_p.add_argument("--version", action="version", version=f"lpp {__version__}")
    compile_p.add_argument("file", help=".lpp source file or directory")
    compile_p.add_argument("-o", "--output", help="write Python output to file instead of stdout")
    compile_p.add_argument("--run", action="store_true", help="execute transpiled Python immediately")
    compile_p.add_argument("--check", action="store_true",
                           help="validate only — parse without emitting output (exits 1 on error)")
    args = compile_p.parse_args(argv)

    if args.check and (args.run or args.output):
        print("lpp: error: --check is mutually exclusive with --run and -o", file=sys.stderr)
        sys.exit(1)

    if os.path.isdir(args.file):
        if args.run:
            print("lpp: error: --run is not supported for directory input", file=sys.stderr)
            sys.exit(1)
        if args.check:
            sys.exit(0 if _check_dir(args.file) else 1)
        if not args.output:
            print("lpp: error: -o <outdir> is required when input is a directory", file=sys.stderr)
            sys.exit(1)
        sys.exit(0 if _compile_dir(args.file, args.output) else 1)

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
