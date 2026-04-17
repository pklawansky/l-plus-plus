# src/lpp/parser.py
from .tokens import Token, TokenType
from .lexer import Lexer
from .ast_nodes import *

class ParseError(Exception):
    def __init__(self, message: str, line: int | None = None, col: int | None = None, expected: str | None = None):
        super().__init__(message)
        self.line = line
        self.col = col
        self.expected = expected

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # --- Helpers ---

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def peek_type(self) -> TokenType:
        return self.tokens[self.pos].type

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, tt: TokenType) -> Token:
        tok = self.advance()
        if tok.type != tt:
            raise ParseError(
                f"expected {tt.name}, got {tok.type.name} ({tok.value!r})",
                line=tok.line, col=tok.col,
                expected=tt.name,
            )
        return tok

    def match(self, *types: TokenType) -> bool:
        return self.peek_type() in types

    def skip_newlines(self) -> None:
        while self.match(TokenType.NEWLINE):
            self.advance()

    def _is_decorator_context(self) -> bool:
        save = self.pos
        try:
            while self.peek_type() == TokenType.AT:
                self.advance()  # consume @
                depth = 0
                while True:
                    tt = self.peek_type()
                    if tt == TokenType.EOF:
                        break
                    if tt == TokenType.NEWLINE and depth == 0:
                        break
                    if tt in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
                        depth += 1
                    elif tt in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
                        depth -= 1
                    self.advance()
                if self.match(TokenType.NEWLINE):
                    self.advance()
                self.skip_newlines()
            return self.peek_type() in (TokenType.DEF, TokenType.CLASS)
        finally:
            self.pos = save

    # --- String interpolation ---

    def _parse_string_literal(self, raw: str) -> StringLiteral:
        """Parse a raw string value containing $...$ interpolation markers."""
        parts: list[str | Expression] = []
        i = 0
        current = ""
        while i < len(raw):
            if raw[i] == "$":
                if i + 1 < len(raw) and raw[i + 1] == "$":
                    current += "$"
                    i += 2
                else:
                    end = raw.find("$", i + 1)
                    if end == -1:
                        current += raw[i:]
                        break
                    if current:
                        parts.append(current)
                        current = ""
                    expr_src = raw[i + 1:end]
                    expr_tokens = Lexer(expr_src).tokenize()
                    expr = Parser(expr_tokens).parse_expression()
                    parts.append(expr)
                    i = end + 1
            else:
                current += raw[i]
                i += 1
        if current:
            parts.append(current)
        return StringLiteral(parts)

    # --- Expression parsing ---

    def parse_expression(self) -> Expression:
        return self._parse_ternary()

    def _parse_ternary(self) -> Expression:
        value = self._parse_pipeline()
        if self.match(TokenType.IF):
            self.advance()
            condition = self._parse_pipeline()
            self.expect(TokenType.ELSE)
            else_value = self._parse_pipeline()
            return TernaryOp(value, condition, else_value)
        return value

    def _parse_pipeline(self) -> Expression:
        left = self._parse_lambda()
        if not self.match(TokenType.PIPE):
            return left
        steps = [left]
        while self.match(TokenType.PIPE):
            self.advance()
            steps.append(self._parse_lambda())
        return Pipeline(steps)

    def _parse_lambda(self) -> Expression:
        # Lambda: ident -> expr  OR  ident,ident -> expr
        # Lookahead to distinguish `x->...` from just `x`
        save = self.pos
        try:
            params = []
            if self.match(TokenType.IDENT):
                params.append(self.advance().value)
                while self.match(TokenType.COMMA):
                    self.advance()
                    params.append(self.expect(TokenType.IDENT).value)
                if self.match(TokenType.ARROW):
                    self.advance()
                    body = self._parse_compose()
                    return Lambda(params, body)
            self.pos = save
        except ParseError:
            self.pos = save
        return self._parse_compose()

    def _parse_compose(self) -> Expression:
        left = self._parse_or()
        while self.match(TokenType.AMP):
            self.advance()
            right = self._parse_or()
            left = Compose(left, right)
        return left

    def _parse_or(self) -> Expression:
        left = self._parse_and()
        while self.peek_type() == TokenType.IDENT and self.peek().value == "or":
            self.advance()
            right = self._parse_and()
            left = BinOp(left, "or", right)
        return left

    def _parse_and(self) -> Expression:
        left = self._parse_not()
        while self.peek_type() == TokenType.IDENT and self.peek().value == "and":
            self.advance()
            right = self._parse_not()
            left = BinOp(left, "and", right)
        return left

    def _parse_not(self) -> Expression:
        if self.match(TokenType.TILDE):
            self.advance()
            return UnaryOp("not", self._parse_not())
        return self._parse_comparison()

    def _parse_comparison(self) -> Expression:
        left = self._parse_additive()
        OPS = {
            TokenType.EQEQ: "==", TokenType.NEQ: "!=",
            TokenType.LT: "<", TokenType.GT: ">",
            TokenType.LTE: "<=", TokenType.GTE: ">=",
        }
        if self.peek_type() in OPS:
            op = OPS[self.advance().type]
            right = self._parse_additive()
            return BinOp(left, op, right)
        if self.peek_type() == TokenType.IN:
            self.advance()
            right = self._parse_additive()
            return BinOp(left, "in", right)
        return left

    def _parse_additive(self) -> Expression:
        left = self._parse_multiplicative()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.advance().value
            right = self._parse_multiplicative()
            left = BinOp(left, op, right)
        return left

    def _parse_multiplicative(self) -> Expression:
        left = self._parse_unary()
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance().value
            right = self._parse_unary()
            left = BinOp(left, op, right)
        return left

    def _parse_unary(self) -> Expression:
        if self.match(TokenType.MINUS):
            self.advance()
            return UnaryOp("-", self._parse_postfix())
        return self._parse_postfix()

    def _parse_postfix(self) -> Expression:
        expr = self._parse_primary()
        while True:
            if self.match(TokenType.BANG):
                self.advance()
                expr = ZeroArgCall(expr)
            elif self.match(TokenType.DOT):
                self.advance()
                attr = self.expect(TokenType.IDENT).value
                expr = Attribute(expr, attr)
            elif self.match(TokenType.LPAREN):
                expr = self._parse_call(expr)
            elif self.match(TokenType.LBRACKET):
                self.advance()
                key = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                expr = Subscript(expr, key)
            else:
                break
        return expr

    def _parse_call(self, func: Expression) -> Call:
        self.expect(TokenType.LPAREN)
        args = []
        kwargs = {}
        while not self.match(TokenType.RPAREN, TokenType.EOF):
            # keyword arg: ident=expr
            if self.peek_type() == TokenType.IDENT and self.tokens[self.pos + 1].type == TokenType.EQ:
                key = self.advance().value
                self.advance()  # skip =
                kwargs[key] = self.parse_expression()
            else:
                if self.match(TokenType.STAR):
                    self.advance()
                    args.append(Spread(self.parse_expression()))
                else:
                    args.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.advance()
        self.expect(TokenType.RPAREN)
        return Call(func, args, kwargs)

    def _parse_primary(self) -> Expression:
        tok = self.peek()

        if tok.type == TokenType.NUMBER:
            self.advance()
            val = tok.value
            return NumberLiteral(float(val) if "." in val else int(val))

        if tok.type == TokenType.STRING:
            self.advance()
            return self._parse_string_literal(tok.value)

        if tok.type == TokenType.AT:
            self.advance()
            attr = self.expect(TokenType.IDENT).value
            return SelfAttr(attr)

        if tok.type == TokenType.IDENT:
            self.advance()
            return Name(tok.value)

        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        if tok.type == TokenType.LBRACKET:
            self.advance()
            elements = []
            while not self.match(TokenType.RBRACKET, TokenType.EOF):
                elements.append(self.parse_expression())
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RBRACKET)
            return ListLiteral(elements)

        if tok.type == TokenType.LBRACE:
            self.advance()
            pairs = []
            while not self.match(TokenType.RBRACE, TokenType.EOF):
                key = self.parse_expression()
                self.expect(TokenType.COLON)
                val = self.parse_expression()
                pairs.append((key, val))
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RBRACE)
            return DictLiteral(pairs)

        raise ParseError(
            f"unexpected token {tok.type.name} ({tok.value!r})",
            line=tok.line, col=tok.col
        )

    # --- Statement parsing ---

    def parse(self) -> Program:
        self.skip_newlines()
        body = []
        while not self.match(TokenType.EOF):
            body.append(self._parse_statement())
            self.skip_newlines()
        return Program(body)

    def _parse_block(self) -> list[Statement]:
        self.expect(TokenType.INDENT)
        stmts = []
        self.skip_newlines()
        while not self.match(TokenType.DEDENT, TokenType.EOF):
            stmts.append(self._parse_statement())
            self.skip_newlines()
        if self.match(TokenType.DEDENT):
            self.advance()
        return stmts

    def _parse_statement(self) -> Statement:
        tt = self.peek_type()

        if tt == TokenType.DEF:
            return self._parse_function()
        if tt == TokenType.CLASS:
            return self._parse_class()
        if tt == TokenType.IF:
            return self._parse_if()
        if tt == TokenType.FOR:
            return self._parse_for()
        if tt == TokenType.WHILE:
            return self._parse_while()
        if tt == TokenType.TRY:
            return self._parse_try()
        if tt == TokenType.RETURN:
            return self._parse_return()
        if tt == TokenType.USE:
            return self._parse_use()
        if tt == TokenType.ALIAS:
            return self._parse_alias()
        if tt == TokenType.BREAK:    return self._parse_break()
        if tt == TokenType.CONTINUE: return self._parse_continue()
        if tt == TokenType.GLOBAL:   return self._parse_global()
        if tt == TokenType.NL:       return self._parse_nonlocal()
        if tt == TokenType.RAISE:    return self._parse_raise()
        if tt == TokenType.WITH:     return self._parse_with()

        # Could be assignment, aug-assignment, append, or expression statement
        return self._parse_expr_or_assign()

    def _parse_function(self) -> FunctionDef:
        self.expect(TokenType.DEF)
        is_method = self.match(TokenType.AT)
        if is_method:
            self.advance()
        name = self.expect(TokenType.IDENT).value
        params = self._parse_params()
        self.skip_newlines()
        body = self._parse_block()
        return FunctionDef(name, params, body, is_method)

    def _parse_params(self) -> list[Param]:
        params = []
        while self.match(TokenType.IDENT):
            pname = self.advance().value
            default = None
            if self.match(TokenType.EQ):
                self.advance()
                default = self.parse_expression()
            params.append(Param(pname, default))
        return params

    def _parse_class(self) -> ClassDef:
        self.expect(TokenType.CLASS)
        name = self.expect(TokenType.IDENT).value
        base = None
        if self.match(TokenType.COLON):
            self.advance()
            base = self.expect(TokenType.IDENT).value
        self.skip_newlines()
        self.expect(TokenType.INDENT)
        methods = []
        self.skip_newlines()
        while not self.match(TokenType.DEDENT, TokenType.EOF):
            methods.append(self._parse_function())
            self.skip_newlines()
        if self.match(TokenType.DEDENT):
            self.advance()
        return ClassDef(name, base, methods)

    def _parse_if(self) -> IfStatement:
        self.expect(TokenType.IF)
        condition = self.parse_expression()
        self.skip_newlines()
        body = self._parse_block()
        elifs = []
        while self.match(TokenType.ELIF, TokenType.ELSE):
            if self.match(TokenType.ELSE):
                self.advance()
                self.skip_newlines()
                elifs.append((None, self._parse_block()))
                break
            else:  # ELIF
                self.advance()
                cond = self.parse_expression()
                self.skip_newlines()
                elifs.append((cond, self._parse_block()))
        return IfStatement(condition, body, elifs)

    def _parse_for(self) -> ForStatement:
        self.expect(TokenType.FOR)
        targets = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.COMMA):
            self.advance()
            targets.append(self.expect(TokenType.IDENT).value)
        self.expect(TokenType.IN)
        iterable = self.parse_expression()
        self.skip_newlines()
        body = self._parse_block()
        return ForStatement(targets, iterable, body)

    def _parse_while(self) -> DoStatement:
        self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        self.skip_newlines()
        body = self._parse_block()
        return DoStatement(condition, body)

    def _parse_try(self) -> TryStatement:
        self.expect(TokenType.TRY)
        self.skip_newlines()
        body = self._parse_block()
        handlers = []
        while self.match(TokenType.EXCEPT):
            self.advance()
            exc_type = None
            name = None
            if self.match(TokenType.IDENT):
                exc_type = self.advance().value
            if self.match(TokenType.IDENT):
                name = self.advance().value
            self.skip_newlines()
            hbody = self._parse_block()
            handlers.append(ErrHandler(exc_type, name, hbody))
        finally_body = None
        if self.match(TokenType.FINALLY):
            self.advance()
            self.skip_newlines()
            finally_body = self._parse_block()
        if not handlers and finally_body is None:
            tok = self.peek()
            raise ParseError(
                "try block requires at least one except handler or finally clause",
                line=tok.line, col=tok.col
            )
        return TryStatement(body, handlers, finally_body)

    def _parse_return(self) -> RetStatement:
        self.expect(TokenType.RETURN)
        value = None
        if not self.match(TokenType.NEWLINE, TokenType.EOF):
            value = self.parse_expression()
        if self.match(TokenType.NEWLINE):
            self.advance()
        return RetStatement(value)

    def _parse_use(self) -> UseStatement:
        self.expect(TokenType.USE)
        imports = []
        from_module = None  # set when parsing module:item[,item] form
        while True:
            alias = None
            item = None
            if from_module is not None:
                # Continuation of a module:item,item2 form — read next item
                item = self.expect(TokenType.IDENT).value
                if self.match(TokenType.EQ):
                    self.advance()
                    alias = self.expect(TokenType.IDENT).value
                imports.append(UseImport(from_module, item, alias))
                if not self.match(TokenType.COMMA):
                    from_module = None
                    break
                self.advance()
                continue
            # Could be: ident, alias=module, module.sub, module:item, module.sub:item
            # Peek ahead for alias= pattern: np=numpy OR np=os.path both work
            if (self.peek_type() == TokenType.IDENT and
                    self.tokens[self.pos + 1].type == TokenType.EQ):
                alias = self.advance().value
                self.advance()  # skip =
            # Read dotted module name: ident (. ident)*
            module = self.expect(TokenType.IDENT).value
            while self.match(TokenType.DOT):
                self.advance()
                module += "." + self.expect(TokenType.IDENT).value
            if self.match(TokenType.COLON):
                self.advance()
                item = self.expect(TokenType.IDENT).value
                if self.match(TokenType.EQ):
                    self.advance()
                    alias = self.expect(TokenType.IDENT).value
                imports.append(UseImport(module, item, alias))
                # If followed by comma, subsequent idents are more items from same module
                if self.match(TokenType.COMMA):
                    self.advance()
                    from_module = module
                    continue
            else:
                imports.append(UseImport(module, item, alias))
            if not self.match(TokenType.COMMA):
                break
            self.advance()
        if self.match(TokenType.NEWLINE):
            self.advance()
        return UseStatement(imports)

    def _parse_alias(self) -> AliasStatement:
        self.expect(TokenType.ALIAS)
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.EQ)
        target = self.parse_expression()
        if self.match(TokenType.NEWLINE):
            self.advance()
        return AliasStatement(name, target)

    def _parse_break(self) -> BreakStatement:
        self.expect(TokenType.BREAK)
        if self.match(TokenType.NEWLINE): self.advance()
        return BreakStatement()

    def _parse_continue(self) -> ContinueStatement:
        self.expect(TokenType.CONTINUE)
        if self.match(TokenType.NEWLINE): self.advance()
        return ContinueStatement()

    def _parse_global(self) -> GlobalStatement:
        self.expect(TokenType.GLOBAL)
        names = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.COMMA):
            self.advance()
            names.append(self.expect(TokenType.IDENT).value)
        if self.match(TokenType.NEWLINE): self.advance()
        return GlobalStatement(names)

    def _parse_nonlocal(self) -> NonlocalStatement:
        self.expect(TokenType.NL)
        names = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.COMMA):
            self.advance()
            names.append(self.expect(TokenType.IDENT).value)
        if self.match(TokenType.NEWLINE): self.advance()
        return NonlocalStatement(names)

    def _parse_raise(self) -> RaiseStatement:
        self.expect(TokenType.RAISE)
        exc = None
        cause = None
        if not self.match(TokenType.NEWLINE, TokenType.EOF):
            exc = self.parse_expression()
            if self.match(TokenType.FROM):
                self.advance()
                cause = self.parse_expression()
        if self.match(TokenType.NEWLINE): self.advance()
        return RaiseStatement(exc, cause)

    def _parse_with(self) -> WithStatement:
        self.expect(TokenType.WITH)
        items = []
        while True:
            expr = self.parse_expression()
            name = None
            if self.match(TokenType.AS):
                self.advance()
                name = self.expect(TokenType.IDENT).value
            items.append((expr, name))
            if not self.match(TokenType.COMMA):
                break
            self.advance()
        self.skip_newlines()
        body = self._parse_block()
        return WithStatement(items, body)

    def _parse_expr_or_assign(self) -> Statement:
        # Path 1: @attr = / @attr op= (self-attribute assignment)
        if self.peek_type() == TokenType.AT:
            stmt = self._try_parse_self_attr_assign()
            if stmt is not None:
                return stmt
            # Fall through: @x used as a bare SelfAttr expression

        # Path 2: ident,ident[,...] = (unpacking assignment)
        targets = self._try_parse_unpack_targets()
        if targets is not None:
            self.advance()  # skip =
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE): self.advance()
            return UnpackAssignment(targets, value)

        # Path 3: expression, then check for assignment/aug-assignment/append
        expr = self.parse_expression()
        AUG = {
            TokenType.PLUSEQ: "+=", TokenType.MINUSEQ: "-=",
            TokenType.STAREQ: "*=", TokenType.SLASHEQ: "/=",
        }
        if self.peek_type() in AUG:
            op = AUG[self.advance().type]
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE): self.advance()
            target = expr.id if isinstance(expr, Name) else expr
            return AugAssignment(target, op, value)
        if self.match(TokenType.EQ):
            self.advance()
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE): self.advance()
            target = expr.id if isinstance(expr, Name) else expr
            return Assignment(target, value)
        if self.match(TokenType.APPEND):
            self.advance()
            value = self.parse_expression()
            if self.match(TokenType.NEWLINE): self.advance()
            return AppendStatement(expr, value)
        if self.match(TokenType.NEWLINE): self.advance()
        return ExprStatement(expr)

    def _try_parse_self_attr_assign(self) -> Statement | None:
        """Try to parse @attr = expr or @attr op= expr. Returns None if the
        @ token is not followed by an assignment operator (bare SelfAttr read)."""
        save = self.pos
        try:
            self.advance()  # consume @
            attr = self.expect(TokenType.IDENT).value
            AUG = {
                TokenType.PLUSEQ: "+=", TokenType.MINUSEQ: "-=",
                TokenType.STAREQ: "*=", TokenType.SLASHEQ: "/=",
            }
            if self.peek_type() in AUG:
                op = AUG[self.advance().type]
                value = self.parse_expression()
                if self.match(TokenType.NEWLINE): self.advance()
                return AugAssignment(f"self.{attr}", op, value)
            if self.peek_type() == TokenType.EQ:
                self.advance()
                value = self.parse_expression()
                if self.match(TokenType.NEWLINE): self.advance()
                return Assignment(f"self.{attr}", value)
            self.pos = save
            return None
        except ParseError:
            self.pos = save
            return None

    def _try_parse_unpack_targets(self) -> list[Expression] | None:
        """Try to parse a comma-separated target list followed by =.
        Returns list of Name/Spread(Name) nodes if >=2 targets found and = follows.
        Resets position on failure; a single ident= falls through to Path 3."""
        save = self.pos
        targets = []
        try:
            while True:
                if self.match(TokenType.STAR):
                    self.advance()
                    name = self.expect(TokenType.IDENT).value
                    targets.append(Spread(Name(name)))
                elif self.match(TokenType.IDENT):
                    targets.append(Name(self.advance().value))
                else:
                    self.pos = save
                    return None
                if not self.match(TokenType.COMMA):
                    break
                self.advance()
            if len(targets) < 2:
                # Single target — not an unpack; let Path 3 handle ident=
                self.pos = save
                return None
            if not self.match(TokenType.EQ):
                self.pos = save
                return None
            return targets
        except ParseError:
            self.pos = save
            return None
