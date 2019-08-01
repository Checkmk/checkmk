import os
import pytest

pytestmark = pytest.mark.checks

exec (open(os.path.join(os.path.dirname(__file__), '../../../checks/jolokia.include')).read())


@pytest.mark.parametrize('line,length,result', [
    (list('ABCDEF'), 3, ["A", "B C D E", "F"]),
    (list('ABCDEF'), 4, ["A", "B C D", "E", "F"]),
    (list('AB'), 2, list("AB")),
])
def test_jolokia_basic_split(line, length, result):
    split_up = jolokia_basic_split(line, length)
    assert result == split_up


@pytest.mark.parametrize('line,length', [
    (['too', 'short'], 3),
    (['too', 'short', 'aswell'], 4),
])
def test_jolokia_basic_split_fail_value(line, length):
    with pytest.raises(ValueError):
        jolokia_basic_split(line, length)


@pytest.mark.parametrize('line,length', [
    (['too', 'short'], 1),
])
def test_jolokia_basic_split_fail_notimplemented(line, length):
    with pytest.raises(NotImplementedError):
        jolokia_basic_split(line, length)
