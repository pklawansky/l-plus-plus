# src/lpp/__init__.py
from importlib.metadata import version as _get_version, PackageNotFoundError
try:
    __version__ = _get_version("lpp")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

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
