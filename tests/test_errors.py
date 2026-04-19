import re
from lpp.errors import format_error


class FakeError(Exception):
    def __init__(self, msg, line=None, col=None, expected=None):
        super().__init__(msg)
        self.line = line
        self.col = col
        self.expected = expected


SOURCE = "first line\nsecond line\nthird line\nfourth line\nfifth line"


def test_plain_text_format():
    err = FakeError("expected COLON", line=4, col=8, expected="COLON")
    result = format_error("error", err, SOURCE, filename="foo.lpp", use_color=False)
    assert result == (
        "error: expected COLON\n"
        " --> foo.lpp:4:8\n"
        "   |\n"
        " 2 | second line\n"
        " 3 | third line\n"
        " 4 | fourth line\n"
        "   |        ^ expected COLON"
    )


def test_no_snippet_without_line():
    err = FakeError("something went wrong")
    result = format_error("error", err, SOURCE, use_color=False)
    assert result == "error: something went wrong"


def test_filename_in_location():
    err = FakeError("oops", line=2, col=1)
    result = format_error("error", err, SOURCE, filename="bar.lpp", use_color=False)
    assert " --> bar.lpp:2:1" in result


def test_no_filename_in_location():
    err = FakeError("oops", line=2, col=1)
    result = format_error("error", err, SOURCE, filename=None, use_color=False)
    assert " --> 2:1" in result
    assert "None" not in result


def test_two_context_lines():
    err = FakeError("bad", line=4, col=1)
    result = format_error("error", err, SOURCE, use_color=False)
    source_lines = [l for l in result.splitlines() if re.match(r'\s+\d+ \| ', l)]
    assert len(source_lines) == 3
    assert any("second line" in l for l in source_lines)
    assert any("third line" in l for l in source_lines)
    assert any("fourth line" in l for l in source_lines)


def test_context_clamped_at_start():
    err = FakeError("bad", line=1, col=1)
    result = format_error("error", err, SOURCE, use_color=False)
    source_lines = [l for l in result.splitlines() if re.match(r'\s+\d+ \| ', l)]
    assert len(source_lines) == 1
    assert "first line" in source_lines[0]


def test_caret_column_correct():
    # line=1 ("first line"), col=3 → ^ under the 3rd char
    err = FakeError("bad", line=1, col=3)
    result = format_error("error", err, SOURCE, use_color=False)
    caret_line = result.splitlines()[-1]
    # gw=2 → gp="   " (3 chars), pipe="|", space → 5 chars prefix before source content
    content_after_gutter = caret_line[5:]
    assert content_after_gutter == "  ^"  # 2 spaces (col-1) then ^


def test_no_caret_without_col():
    err = FakeError("bad", line=2)
    result = format_error("error", err, SOURCE, use_color=False)
    assert "^" not in result


def test_gutter_width_single_digit():
    # line <= 9 → gw=max(2,1)=2 → gp="   " (3 chars) → separator "   |"
    err = FakeError("bad", line=5, col=1)
    result = format_error("error", err, SOURCE, use_color=False)
    sep_line = result.splitlines()[2]
    assert sep_line == "   |"


def test_gutter_width_multi_digit():
    # line=100 → gw=max(2,3)=3 → gp="    " (4 chars) → separator "    |"
    long_source = "\n".join(f"line {i}" for i in range(1, 101))
    err = FakeError("bad", line=100, col=1)
    result = format_error("error", err, long_source, use_color=False)
    lines = result.splitlines()
    assert lines[2] == "    |"
    assert any("100 |" in l for l in lines)


def test_expected_annotation():
    err = FakeError("got INT", line=2, col=1, expected="COLON")
    result = format_error("error", err, SOURCE, use_color=False)
    assert "^ expected COLON" in result


def test_color_codes_present():
    err = FakeError("bad", line=2, col=1)
    result = format_error("error", err, SOURCE, use_color=True)
    assert "\033[" in result
