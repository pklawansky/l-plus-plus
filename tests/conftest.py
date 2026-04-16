# tests/conftest.py
import pytest
from lpp import compile_lpp

@pytest.fixture
def lpp():
    def _compile(source: str) -> str:
        return compile_lpp(source)
    return _compile
