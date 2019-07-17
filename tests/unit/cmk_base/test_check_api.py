import ast
from cmk_base import check_api


def test_as_float():
    assert check_api.as_float('8.00') == 8.0
    assert str(check_api.as_float('inf')) == 'inf'

    strrep = str(list(map(check_api.as_float, ("8", "-inf", '1e-351'))))
    assert strrep == '[8.0, -1e309, 0.0]'

    assert ast.literal_eval(strrep) == [8.0, float('-inf'), 0.0]
