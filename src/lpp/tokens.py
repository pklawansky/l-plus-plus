from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    # Keywords
    FN = auto()
    CLS = auto()
    IF = auto()
    EL = auto()
    FOR = auto()
    IN = auto()
    DO = auto()
    RET = auto()
    TRY = auto()
    ERR = auto()
    USE = auto()
    ALIAS = auto()
    BREAK = auto()
    CONTINUE = auto()
    RAISE = auto()
    WITH = auto()
    AS = auto()
    FIN = auto()
    GLOBAL = auto()
    NL = auto()
    FROM = auto()
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    # Operators
    PIPE = auto()       # |
    ARROW = auto()      # ->
    AT = auto()         # @
    BANG = auto()       # !
    TILDE = auto()      # ~
    AMP = auto()        # &
    APPEND = auto()     # <<
    COLON = auto()      # :
    # Arithmetic / comparison
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    PLUSEQ = auto()
    MINUSEQ = auto()
    STAREQ = auto()
    SLASHEQ = auto()
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    DOT = auto()
    # Structural
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()

KEYWORDS: dict[str, TokenType] = {
    "fn": TokenType.FN,
    "cls": TokenType.CLS,
    "if": TokenType.IF,
    "el": TokenType.EL,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "do": TokenType.DO,
    "ret": TokenType.RET,
    "try": TokenType.TRY,
    "err": TokenType.ERR,
    "use": TokenType.USE,
    "alias": TokenType.ALIAS,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "raise": TokenType.RAISE,
    "with": TokenType.WITH,
    "as": TokenType.AS,
    "fin": TokenType.FIN,
    "global": TokenType.GLOBAL,
    "nl": TokenType.NL,
    "from": TokenType.FROM,
}

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int = 0
