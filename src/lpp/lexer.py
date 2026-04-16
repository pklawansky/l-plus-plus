# src/lpp/lexer.py
from .tokens import Token, TokenType, KEYWORDS

class LexError(Exception):
    def __init__(self, message: str, line: int | None = None, col: int | None = None):
        super().__init__(message)
        self.line = line
        self.col = col

class Lexer:
    def __init__(self, source: str):
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.pos = 0
        self.line = 1
        self.line_start = 0
        self.tokens: list[Token] = []
        self.indent_stack: list[int] = [0]

    def peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else ""

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.line_start = self.pos
        return ch

    def add(self, type: TokenType, value: str = "") -> None:
        col = self.pos - len(value) - self.line_start + 1
        self.tokens.append(Token(type, value, self.line, col))

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.source):
            self._scan_line()
        # Close any open indents
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.add(TokenType.DEDENT)
        self.add(TokenType.EOF)
        return self.tokens

    def _scan_line(self) -> None:
        # Measure indent at start of line
        indent = 0
        while self.peek() == " ":
            indent += 1
            self.pos += 1

        # Blank line or comment-only line — skip without emitting NEWLINE
        if self.peek() in ("", "\n", "#"):
            while self.peek() not in ("", "\n"):
                self.pos += 1
            if self.peek() == "\n":
                self.pos += 1
                self.line += 1
                self.line_start = self.pos
            return

        # Handle indent/dedent
        current = self.indent_stack[-1]
        if indent > current:
            self.indent_stack.append(indent)
            self.add(TokenType.INDENT)
        elif indent < current:
            while self.indent_stack[-1] > indent:
                self.indent_stack.pop()
                self.add(TokenType.DEDENT)
            if self.indent_stack[-1] != indent:
                raise LexError(
                    f"unexpected indentation level {indent}",
                    line=self.line, col=indent + 1
                )

        # Scan tokens on this line
        while self.peek() not in ("", "\n"):
            self._scan_token()

        if self.peek() == "\n":
            self.add(TokenType.NEWLINE)
            self.pos += 1
            self.line += 1
            self.line_start = self.pos

    def _scan_token(self) -> None:
        ch = self.peek()

        if ch == " ":
            self.pos += 1
            return

        if ch == "#":
            while self.peek() not in ("", "\n"):
                self.pos += 1
            return

        if ch == '"':
            self._scan_string()
            return

        if ch.isdigit() or (ch == "-" and self.peek(1).isdigit() and
                            (not self.tokens or
                             self.tokens[-1].type in (TokenType.EQ, TokenType.LPAREN,
                                                       TokenType.COMMA, TokenType.NEWLINE,
                                                       TokenType.INDENT))):
            self._scan_number()
            return

        if ch.isalpha() or ch == "_":
            self._scan_word()
            return

        self._scan_operator()

    def _scan_string(self) -> None:
        string_col = self.pos - self.line_start + 1  # column of opening "
        self.pos += 1  # skip opening "
        value = ""
        while self.peek() not in ('"', "", "\n"):
            if self.peek() == "\\":
                self.pos += 1
                esc = self.advance()
                value += {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc)
            else:
                value += self.advance()
        if self.peek() != '"':
            raise LexError(
                "unterminated string literal",
                line=self.line, col=string_col
            )
        self.pos += 1
        self.tokens.append(Token(TokenType.STRING, value, self.line, string_col))

    def _scan_number(self) -> None:
        start = self.pos
        if self.peek() == "-":
            self.pos += 1
        while self.peek().isdigit():
            self.pos += 1
        if self.peek() == "." and self.peek(1).isdigit():
            self.pos += 1
            while self.peek().isdigit():
                self.pos += 1
        self.add(TokenType.NUMBER, self.source[start:self.pos])

    def _scan_word(self) -> None:
        start = self.pos
        while self.peek().isalnum() or self.peek() == "_":
            self.pos += 1
        word = self.source[start:self.pos]
        tt = KEYWORDS.get(word, TokenType.IDENT)
        self.add(tt, word)

    def _scan_operator(self) -> None:
        ch = self.advance()
        two = ch + self.peek()

        MAP2 = {
            "->": TokenType.ARROW, "<<": TokenType.APPEND,
            "==": TokenType.EQEQ, "!=": TokenType.NEQ,
            "<=": TokenType.LTE,  ">=": TokenType.GTE,
            "+=": TokenType.PLUSEQ, "-=": TokenType.MINUSEQ,
            "*=": TokenType.STAREQ, "/=": TokenType.SLASHEQ,
        }
        MAP1 = {
            "|": TokenType.PIPE, "@": TokenType.AT, "!": TokenType.BANG,
            "~": TokenType.TILDE, "&": TokenType.AMP, ":": TokenType.COLON,
            "(": TokenType.LPAREN, ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
            "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            ",": TokenType.COMMA, ".": TokenType.DOT,
            "=": TokenType.EQ, "<": TokenType.LT, ">": TokenType.GT,
            "+": TokenType.PLUS, "-": TokenType.MINUS,
            "*": TokenType.STAR, "/": TokenType.SLASH, "%": TokenType.PERCENT,
        }

        if two in MAP2:
            self.pos += 1
            self.add(MAP2[two], two)
        elif ch in MAP1:
            self.add(MAP1[ch], ch)
        else:
            raise LexError(
                f"unexpected character {ch!r}",
                line=self.line, col=self.pos - self.line_start
            )
