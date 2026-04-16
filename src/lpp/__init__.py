# src/lpp/__init__.py
try:
    from .lexer import Lexer
    from .parser import Parser
    from .transpiler import Transpiler

    def compile_lpp(source: str) -> str:
        tokens = Lexer(source).tokenize()
        tree = Parser(tokens).parse()
        return Transpiler().transpile(tree)

except ImportError:
    def compile_lpp(source: str) -> str:  # type: ignore[misc]
        raise NotImplementedError(
            "lpp modules (lexer, parser, transpiler) are not yet implemented."
        )
