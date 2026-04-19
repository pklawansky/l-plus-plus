import sys


def _ansi(code: str, text: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def _gutter_width(line_no: int) -> int:
    return max(2, len(str(line_no)))


def format_error(
    label: str,
    err: Exception,
    source: str,
    filename: str | None = None,
    use_color: bool | None = None,
) -> str:
    if use_color is None:
        use_color = sys.stderr.isatty()

    line = getattr(err, "line", None)
    col = getattr(err, "col", None)
    expected = getattr(err, "expected", None)

    parts = [f"{_ansi('1;31', f'{label}:', use_color)} {err}"]

    if not line:
        return parts[0]

    loc_parts = []
    if filename:
        loc_parts.append(filename)
    loc_parts.append(str(line))
    if col is not None:
        loc_parts.append(str(col))
    parts.append(f" {_ansi('1;36', '-->', use_color)} {':'.join(loc_parts)}")

    src_lines = source.splitlines() if source else []
    gw = _gutter_width(line)
    gp = " " * (gw + 1)
    pipe = _ansi("1;36", "|", use_color)

    parts.append(f"{gp}{pipe}")

    start = max(1, line - 2)
    for n in range(start, line + 1):
        if 0 < n <= len(src_lines):
            num = _ansi("1;36", str(n).rjust(gw), use_color)
            parts.append(f"{num} {pipe} {src_lines[n - 1]}")

    if col is not None:
        caret = _ansi("1;31", "^", use_color)
        annotation = f" expected {expected}" if expected else ""
        parts.append(f"{gp}{pipe} {' ' * (col - 1)}{caret}{annotation}")

    return "\n".join(parts)
