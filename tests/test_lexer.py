# tests/test_lexer.py  (replace existing stub)
import pytest
from lpp.tokens import TokenType, Token
from lpp.lexer import Lexer

def tokenize(src: str) -> list[Token]:
    return Lexer(src).tokenize()

def types(src: str) -> list[TokenType]:
    return [t.type for t in tokenize(src) if t.type != TokenType.EOF]

def test_token_creation():
    t = Token(TokenType.IDENT, "foo", line=1)
    assert t.type == TokenType.IDENT

def test_keywords():
    assert types("fn") == [TokenType.FN]
    assert types("if el for in do ret try err use alias cls") == [
        TokenType.IF, TokenType.EL, TokenType.FOR, TokenType.IN,
        TokenType.DO, TokenType.RET, TokenType.TRY, TokenType.ERR,
        TokenType.USE, TokenType.ALIAS, TokenType.CLS,
    ]

def test_identifiers():
    assert types("foo bar x y1") == [TokenType.IDENT] * 4

def test_numbers():
    toks = tokenize("42 3.14")
    assert toks[0].type == TokenType.NUMBER and toks[0].value == "42"
    assert toks[1].type == TokenType.NUMBER and toks[1].value == "3.14"

def test_string_literal():
    toks = tokenize('"hello world"')
    assert toks[0].type == TokenType.STRING
    assert toks[0].value == "hello world"

def test_operators():
    assert types("| -> @ ! ~ & <<") == [
        TokenType.PIPE, TokenType.ARROW, TokenType.AT,
        TokenType.BANG, TokenType.TILDE, TokenType.AMP, TokenType.APPEND,
    ]

def test_comparison_ops():
    assert types("== != < > <= >=") == [
        TokenType.EQEQ, TokenType.NEQ, TokenType.LT,
        TokenType.GT, TokenType.LTE, TokenType.GTE,
    ]

def test_indent_dedent():
    src = "fn foo\n  x\n"
    toks = tokenize(src)
    tt = [t.type for t in toks]
    assert TokenType.INDENT in tt
    assert TokenType.DEDENT in tt

def test_comments_stripped():
    assert types("x=1 # a comment\ny=2") == [
        TokenType.IDENT, TokenType.EQ, TokenType.NUMBER,
        TokenType.NEWLINE,
        TokenType.IDENT, TokenType.EQ, TokenType.NUMBER,
    ]

def test_string_with_interpolation_markers():
    toks = tokenize('"hello $name$!"')
    assert toks[0].type == TokenType.STRING
    # raw value preserved including $ markers — parser handles interpolation
    assert "$name$" in toks[0].value

def test_unterminated_string_raises():
    from lpp.lexer import LexError
    with pytest.raises(LexError, match="[Uu]nterminated"):
        tokenize('"hello')

def test_double_colon_is_two_colons():
    # :: is no longer a dedicated token — lexes as COLON COLON
    result = types("a::b")
    assert result == [TokenType.IDENT, TokenType.COLON, TokenType.COLON, TokenType.IDENT]

def test_as_is_now_a_keyword():
    # 'as' is now a keyword (Tier 2: used in with statements and exception handlers)
    toks = [t for t in Lexer("as\n").tokenize()
            if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
    assert len(toks) == 1
    assert toks[0].type == TokenType.AS
    assert toks[0].value == "as"

def test_lex_error_has_line_and_col():
    from lpp.lexer import LexError
    try:
        Lexer('"unterminated\n').tokenize()
        assert False, "expected LexError"
    except LexError as e:
        assert e.line == 1
        assert e.col is not None
        assert e.col > 0

def test_token_has_col():
    tokens = Lexer("x = 42\n").tokenize()
    ident = tokens[0]
    assert ident.value == "x"
    assert ident.col == 1
    eq = tokens[1]
    assert eq.col == 3

def test_token_col_on_second_line():
    # Ensure line_start resets correctly so col is 1-based from the line start
    tokens = Lexer("a=1\ny=2\n").tokenize()
    # tokens: IDENT(a,1,1) EQ(=,1,2) NUMBER(1,1,3) NEWLINE IDENT(y,2,1) EQ(=,2,2) NUMBER(2,2,3) NEWLINE EOF
    y_tok = next(t for t in tokens if t.value == "y")
    assert y_tok.line == 2
    assert y_tok.col == 1
