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
