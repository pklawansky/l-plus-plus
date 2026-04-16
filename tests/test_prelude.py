# tests/test_prelude.py
from lpp.prelude import PRELUDE, inject_prelude

def test_prelude_contains_single_char():
    for alias in ["p", "l", "r", "s", "i", "f", "b", "t"]:
        assert alias in PRELUDE, f"Missing single-char alias: {alias}"

def test_prelude_contains_two_char():
    for alias in ["li", "di", "se", "tu", "en", "zi", "ma", "fi",
                  "so", "rv", "su", "mn", "mx", "ab", "ro", "an",
                  "al", "nx", "ip", "op", "rp", "ga", "sa", "ha",
                  "od", "ch", "pw", "hx", "isa", "sc"]:
        assert alias in PRELUDE, f"Missing two-char alias: {alias}"

def test_no_alias_conflicts():
    assert len(PRELUDE) == len(set(PRELUDE.keys())), "Duplicate alias keys"
    assert len(PRELUDE) == len(set(PRELUDE.values())), "Duplicate alias targets"

def test_inject_prelude_prepends():
    python_src = "x = 1\n"
    result = inject_prelude(python_src)
    assert result.startswith("# L++ prelude")
    assert "print" in result
    assert "x = 1" in result
