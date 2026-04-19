# Enterprise Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make L++ installable from PyPI and production-ready for CI/CD pipelines with directory compilation and watch mode.

**Architecture:** Keep the current flat CLI shape (`lpp <file|dir> [flags]`) and add a `watch` subcommand for the long-running case. Directory compilation mirrors the source tree into an output directory. No new runtime dependencies — watch mode uses stdlib polling.

**Tech Stack:** Python 3.11+, setuptools, argparse, `importlib.metadata` for version, stdlib `os`/`time` for watch polling.

---

## File Map

| File | Change |
|------|--------|
| `pyproject.toml` | Add full PyPI metadata (description, authors, license, classifiers, URLs) |
| `src/lpp/__init__.py` | Expose `__version__` via `importlib.metadata` |
| `src/lpp/cli.py` | Add `--version`, `--check`, directory support, `watch` subcommand |
| `tests/test_cli.py` | New — CLI integration tests via `subprocess` |
| `README.md` | Update usage section to document new flags and `watch` |

---

### Task 1: PyPI metadata + `__version__`

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/lpp/__init__.py`

- [ ] **Step 1: Update `pyproject.toml`**

Replace the `[project]` section with:

```toml
[project]
name = "lpp"
version = "0.2.0"
description = "A terse Python transpiler — write compact .lpp source, emit idiomatic Python"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Phillip Klawansky", email = "pklawansky@gmail.com" }]
keywords = ["transpiler", "python", "llm", "code-generation"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Code Generators",
    "Topic :: Software Development :: Compilers",
]

[project.urls]
Homepage = "https://github.com/pklawansky/l-plus-plus"
Repository = "https://github.com/pklawansky/l-plus-plus"
Issues = "https://github.com/pklawansky/l-plus-plus/issues"
```

- [ ] **Step 2: Expose `__version__` in `__init__.py`**

Add at the top of `src/lpp/__init__.py`, before the try block:

```python
from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version("lpp")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
```

- [ ] **Step 3: Reinstall the package so metadata is available**

```bash
pip install -e .
```

- [ ] **Step 4: Verify version is accessible**

```bash
python -c "import lpp; print(lpp.__version__)"
```

Expected output: `0.2.0`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/lpp/__init__.py
git commit -m "chore: add PyPI metadata and __version__"
```

---

### Task 2: `--version` flag

**Files:**
- Modify: `src/lpp/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
import subprocess, sys

def lpp(*args):
    """Run the lpp CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "lpp.cli", *args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def test_version_flag():
    code, out, _ = lpp("--version")
    assert code == 0
    assert out.startswith("lpp ")
    assert "." in out  # e.g. "lpp 0.2.0"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py::test_version_flag -v
```

Expected: FAIL — `--version` not recognized

- [ ] **Step 3: Add `--version` to `cli.py`**

In `main()`, add to the `ArgumentParser` after `description=`:

```python
from lpp import __version__

parser.add_argument(
    "--version", action="version",
    version=f"lpp {__version__}"
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_cli.py::test_version_flag -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lpp/cli.py tests/test_cli.py
git commit -m "feat(cli): add --version flag"
```

---

### Task 3: `--check` flag (CI-friendly validate-only)

**Files:**
- Modify: `src/lpp/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:

```python
import tempfile, os

def write_lpp(src: str) -> str:
    """Write L++ source to a temp file, return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".lpp", delete=False)
    f.write(src)
    f.close()
    return f.name

def test_check_valid_file_exits_zero():
    path = write_lpp("x=1\n")
    try:
        code, out, err = lpp(path, "--check")
        assert code == 0
        assert out == ""
    finally:
        os.unlink(path)

def test_check_invalid_file_exits_one():
    path = write_lpp("def\n")  # def with no name — parse error
    try:
        code, out, err = lpp(path, "--check")
        assert code == 1
        assert "error" in err.lower()
    finally:
        os.unlink(path)

def test_check_does_not_emit_python():
    path = write_lpp("x=1\n")
    try:
        code, out, err = lpp(path, "--check")
        assert "x = 1" not in out
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py::test_check_valid_file_exits_zero tests/test_cli.py::test_check_invalid_file_exits_one tests/test_cli.py::test_check_does_not_emit_python -v
```

Expected: 3 FAIL — `--check` not recognized

- [ ] **Step 3: Add `--check` to `cli.py`**

Add argument after `--run`:

```python
parser.add_argument("--check", action="store_true",
                    help="validate only — parse without emitting output (exits 1 on error)")
```

Add handling in `main()` after the `compile_lpp` call — replace the existing output block with:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py::test_check_valid_file_exits_zero tests/test_cli.py::test_check_invalid_file_exits_one tests/test_cli.py::test_check_does_not_emit_python -v
```

Expected: 3 PASS

- [ ] **Step 5: Run full suite to verify no regressions**

```bash
pytest
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/lpp/cli.py tests/test_cli.py
git commit -m "feat(cli): add --check flag for CI validation"
```

---

### Task 4: Directory compilation

**Files:**
- Modify: `src/lpp/cli.py`
- Modify: `tests/test_cli.py`

**Design:** When `<path>` is a directory, find all `*.lpp` files recursively, compile each, write to a parallel structure under `-o <outdir>`. Requires `-o` when input is a directory. Errors in any file are reported but compilation continues; exit 1 if any file had errors.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:

```python
def test_dir_compile_requires_output_flag():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "a.lpp"), "w").write("x=1\n")
        code, out, err = lpp(d)
        assert code == 1
        assert "-o" in err or "output" in err.lower()

def test_dir_compile_creates_py_files():
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as out_dir:
        open(os.path.join(src_dir, "a.lpp"), "w").write("x=1\n")
        open(os.path.join(src_dir, "b.lpp"), "w").write("y=2\n")
        code, out, err = lpp(src_dir, "-o", out_dir)
        assert code == 0
        assert os.path.exists(os.path.join(out_dir, "a.py"))
        assert os.path.exists(os.path.join(out_dir, "b.py"))

def test_dir_compile_mirrors_subdirs():
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as out_dir:
        sub = os.path.join(src_dir, "sub")
        os.makedirs(sub)
        open(os.path.join(sub, "c.lpp"), "w").write("z=3\n")
        code, _, _ = lpp(src_dir, "-o", out_dir)
        assert code == 0
        assert os.path.exists(os.path.join(out_dir, "sub", "c.py"))

def test_dir_compile_exits_one_on_any_error():
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as out_dir:
        open(os.path.join(src_dir, "good.lpp"), "w").write("x=1\n")
        open(os.path.join(src_dir, "bad.lpp"), "w").write("def\n")
        code, _, err = lpp(src_dir, "-o", out_dir)
        assert code == 1
        assert "bad.lpp" in err
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py::test_dir_compile_requires_output_flag tests/test_cli.py::test_dir_compile_creates_py_files tests/test_cli.py::test_dir_compile_mirrors_subdirs tests/test_cli.py::test_dir_compile_exits_one_on_any_error -v
```

Expected: 4 FAIL

- [ ] **Step 3: Implement directory compilation in `cli.py`**

Replace the `main()` body with this expanded version:

```python
def _compile_dir(src_dir: str, out_dir: str) -> bool:
    """Compile all .lpp files under src_dir into out_dir. Returns True if clean."""
    from lpp.lexer import LexError
    from lpp.parser import ParseError
    from lpp import compile_lpp

    clean = True
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith(".lpp"):
                continue
            src_path = os.path.join(root, fname)
            rel = os.path.relpath(src_path, src_dir)
            out_path = os.path.join(out_dir, os.path.splitext(rel)[0] + ".py")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
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


def main() -> None:
    import os
    from lpp import __version__

    parser = argparse.ArgumentParser(
        prog="lpp",
        description="L++ transpiler — compile .lpp files to Python",
    )
    parser.add_argument("--version", action="version", version=f"lpp {__version__}")
    parser.add_argument("file", help=".lpp source file or directory")
    parser.add_argument("-o", "--output", help="output file (single) or directory (when input is a directory)")
    parser.add_argument("--run", action="store_true", help="execute transpiled Python immediately (single file only)")
    parser.add_argument("--check", action="store_true", help="validate only — parse without emitting output (exits 1 on error)")
    args = parser.parse_args()

    if os.path.isdir(args.file):
        if args.check:
            clean = _compile_dir(args.file, None) if False else _check_dir(args.file)
            sys.exit(0 if clean else 1)
        if not args.output:
            print("lpp: error: -o <outdir> is required when input is a directory", file=sys.stderr)
            sys.exit(1)
        clean = _compile_dir(args.file, args.output)
        sys.exit(0 if clean else 1)

    # Single file path
    try:
        with open(args.file) as f:
            source = f.read()
    except FileNotFoundError:
        print(f"lpp: error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    from lpp.lexer import LexError
    from lpp.parser import ParseError
    from lpp import compile_lpp

    try:
        python_src = compile_lpp(source)
    except (LexError, ParseError) as e:
        print(_format_error("error", e, source), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"lpp: internal error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        pass
    elif args.run:
        exec(compile(python_src, args.file, "exec"), {"__name__": "__main__"})
    elif args.output:
        with open(args.output, "w") as f:
            f.write(python_src)
        print(f"Written to {args.output}")
    else:
        print(python_src)
```

Also add `_check_dir` helper before `_compile_dir`:

```python
def _check_dir(src_dir: str) -> bool:
    """Parse-only check of all .lpp files under src_dir. Returns True if clean."""
    from lpp.lexer import LexError
    from lpp.parser import ParseError
    from lpp import compile_lpp

    clean = True
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith(".lpp"):
                continue
            src_path = os.path.join(root, fname)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py::test_dir_compile_requires_output_flag tests/test_cli.py::test_dir_compile_creates_py_files tests/test_cli.py::test_dir_compile_mirrors_subdirs tests/test_cli.py::test_dir_compile_exits_one_on_any_error -v
```

Expected: 4 PASS

- [ ] **Step 5: Run full suite**

```bash
pytest
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/lpp/cli.py tests/test_cli.py
git commit -m "feat(cli): add directory compilation and --check flag for dirs"
```

---

### Task 5: `watch` subcommand

**Files:**
- Modify: `src/lpp/cli.py`
- Modify: `tests/test_cli.py`

**Design:** `lpp watch <file|dir> [-o <outdir>]` polls for `mtime` changes every 500 ms using stdlib only. On change, recompiles and prints a timestamp line. `Ctrl-C` exits cleanly.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
import threading, time

def test_watch_compiles_on_change():
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as out_dir:
        lpp_path = os.path.join(src_dir, "a.lpp")
        out_path = os.path.join(out_dir, "a.py")
        open(lpp_path, "w").write("x=1\n")

        # Start watch in background thread; let it do one pass then kill it
        proc = subprocess.Popen(
            [sys.executable, "-m", "lpp.cli", "watch", src_dir, "-o", out_dir],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        time.sleep(1.5)  # allow one poll cycle
        proc.terminate()
        proc.wait(timeout=3)

        assert os.path.exists(out_path)
        assert "x = 1" in open(out_path).read()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py::test_watch_compiles_on_change -v
```

Expected: FAIL — `watch` is not a recognized argument

- [ ] **Step 3: Add `watch` subcommand to `cli.py`**

Replace `main()` with a version that uses argparse subparsers. Add at the top of `main()`:

```python
def main() -> None:
    import os
    from lpp import __version__

    root_parser = argparse.ArgumentParser(
        prog="lpp",
        description="L++ transpiler — compile .lpp files to Python",
    )
    root_parser.add_argument("--version", action="version", version=f"lpp {__version__}")

    sub = root_parser.add_subparsers(dest="cmd")

    # --- watch subcommand ---
    watch_p = sub.add_parser("watch", help="watch files and recompile on change")
    watch_p.add_argument("file", help=".lpp source file or directory to watch")
    watch_p.add_argument("-o", "--output", required=True, help="output directory")
    watch_p.add_argument("--interval", type=float, default=0.5, help="poll interval in seconds (default 0.5)")

    # --- default: compile/check/run (no subcommand) ---
    root_parser.add_argument("file", nargs="?", help=".lpp source file or directory")
    root_parser.add_argument("-o", "--output", help="output file or directory")
    root_parser.add_argument("--run", action="store_true", help="execute immediately (single file only)")
    root_parser.add_argument("--check", action="store_true", help="validate only, no output")

    args = root_parser.parse_args()

    if args.cmd == "watch":
        _watch(args.file, args.output, args.interval)
        return

    if not args.file:
        root_parser.print_help()
        sys.exit(1)

    # ... (rest of existing single-file / dir logic unchanged)
```

Add `_watch` function above `main()`:

```python
def _watch(src: str, out_dir: str, interval: float) -> None:
    import os, time
    from lpp import compile_lpp
    from lpp.lexer import LexError
    from lpp.parser import ParseError

    def snapshot():
        """Return dict of path -> mtime for all .lpp files under src."""
        result = {}
        if os.path.isfile(src):
            result[src] = os.path.getmtime(src)
        else:
            for root, _, files in os.walk(src):
                for f in files:
                    if f.endswith(".lpp"):
                        p = os.path.join(root, f)
                        result[p] = os.path.getmtime(p)
        return result

    def compile_one(src_path: str) -> None:
        rel = os.path.relpath(src_path, src) if os.path.isdir(src) else os.path.basename(src_path)
        out_path = os.path.join(out_dir, os.path.splitext(rel)[0] + ".py")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        try:
            with open(src_path) as f:
                source = f.read()
            python_src = compile_lpp(source)
            with open(out_path, "w") as f:
                f.write(python_src)
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] compiled {src_path} → {out_path}")
        except (LexError, ParseError) as e:
            print(_format_error(f"error in {src_path}", e, source), file=sys.stderr)
        except Exception as e:
            print(f"lpp: internal error in {src_path}: {e}", file=sys.stderr)

    os.makedirs(out_dir, exist_ok=True)
    prev = {}
    print(f"lpp watch: watching {src} → {out_dir}  (Ctrl-C to stop)")
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_cli.py::test_watch_compiles_on_change -v
```

Expected: PASS

- [ ] **Step 5: Run full suite**

```bash
pytest
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/lpp/cli.py tests/test_cli.py
git commit -m "feat(cli): add watch subcommand with mtime polling"
```

---

### Task 6: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the CLI Usage section in `README.md`**

Find the `## CLI Usage` section and replace it with:

```markdown
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

Recompiles on every file save. Uses stdlib polling — no extra dependencies.

```sh
lpp watch src/ -o out/
lpp watch program.lpp -o .
```

### Version

```sh
lpp --version
```
```

- [ ] **Step 2: Verify the examples section still lists `fizzbuzz.lpp --run`**

Confirm the Quick Example section still reads:

```sh
lpp fizzbuzz.lpp --run
```

(No change needed — the default single-file command is unchanged.)

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update CLI usage for --check, directory, and watch"
```

---

## Self-Review

**Spec coverage:**
- PyPI metadata → Task 1 ✓
- `__version__` → Task 1 ✓
- `--version` → Task 2 ✓
- `--check` (single file) → Task 3 ✓
- `--check` (directory) → Task 4 ✓
- Directory compilation → Task 4 ✓
- `watch` subcommand → Task 5 ✓
- README → Task 6 ✓

**Placeholder scan:** No TBDs found. All code blocks are complete.

**Type consistency:** `_format_error` is defined in the existing `cli.py` and used in `_compile_dir`, `_check_dir`, and `_watch` — consistent. `compile_lpp` imported from `lpp` in all helpers — consistent.

**Note:** Task 4 Step 3 includes an inline `if False` branch in `_check_dir` call that was a leftover from drafting — the final code routes correctly via `args.check` before checking `os.path.isdir`. Review that block carefully during execution and simplify if the logic becomes tangled.
