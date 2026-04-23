from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    # Keywords
    DEF = auto()
    CLASS = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    FOR = auto()
    IN = auto()
    WHILE = auto()
    RETURN = auto()
    TRY = auto()
    EXCEPT = auto()
    USE = auto()
    ALIAS = auto()
    BREAK = auto()
    CONTINUE = auto()
    RAISE = auto()
    WITH = auto()
    AS = auto()
    FINALLY = auto()
    GLOBAL = auto()
    NL = auto()
    FROM = auto()
    IS = auto()
    NOT = auto()
    STARSTAR = auto()
    DOUBLESLASH = auto()
    ASSERT = auto()
    DEL = auto()
    PASS = auto()
    YIELD = auto()
    COLONCOLON = auto()  # ::
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
    PERCENTEQ = auto()
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
    "def": TokenType.DEF,
    "class": TokenType.CLASS,
    "if": TokenType.IF,
    "elif": TokenType.ELIF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "while": TokenType.WHILE,
    "return": TokenType.RETURN,
    "try": TokenType.TRY,
    "except": TokenType.EXCEPT,
    "use": TokenType.USE,
    "alias": TokenType.ALIAS,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "raise": TokenType.RAISE,
    "with": TokenType.WITH,
    "as": TokenType.AS,
    "finally": TokenType.FINALLY,
    "global": TokenType.GLOBAL,
    "nl": TokenType.NL,
    "from": TokenType.FROM,
    "is": TokenType.IS,
    "not": TokenType.NOT,
    "assert": TokenType.ASSERT,
    "del": TokenType.DEL,
    "pass": TokenType.PASS,
    "yield": TokenType.YIELD,
}

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int = 0
