"""main.py 里的辅助函数测试。"""

import pytest

from main import run_bad_code


def test_run_bad_code_executes_valid_code():
    run_bad_code("x = 1")


def test_run_bad_code_passes_through_syntax_error():
    with pytest.raises(SyntaxError):
        run_bad_code("if True print('x')")
