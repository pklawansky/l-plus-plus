import subprocess, sys, tempfile, os

def lpp(*args):
    """Run the lpp CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "lpp.cli", *args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def write_lpp(src: str) -> str:
    """Write L++ source to a temp file, return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".lpp", delete=False)
    f.write(src)
    f.close()
    return f.name

def test_version_flag():
    code, out, err = lpp("--version")
    assert code == 0
    assert err == ""
    assert out.startswith("lpp ")
    assert "." in out  # e.g. "lpp 0.2.0"

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


import time


def test_watch_compiles_on_change():
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as out_dir:
        lpp_path = os.path.join(src_dir, "a.lpp")
        out_path = os.path.join(out_dir, "a.py")
        open(lpp_path, "w").write("x=1\n")

        proc = subprocess.Popen(
            [sys.executable, "-m", "lpp.cli", "watch", src_dir, "-o", out_dir],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        time.sleep(1.5)  # allow one poll cycle
        proc.terminate()
        proc.wait(timeout=3)

        assert os.path.exists(out_path)
        assert "x = 1" in open(out_path).read()

