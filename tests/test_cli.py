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

