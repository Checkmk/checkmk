import pytest  # type: ignore
from cmk.base.check_api import MKCounterWrapped
from checktestlib import CheckResult

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('item,info', [
    ('Service_FOO', [[
        'node_1', 'cached(1556005301,300)', '0', 'Service_FOO', 'V=1', 'This', 'Check', 'is',
        'outdated'
    ]]),
])
def test_local_check(check_manager, monkeypatch, item, info):
    monkeypatch.setattr('time.time', lambda: 1556005721)
    check = check_manager.get_check('local')

    parsed = check.run_parse(info)
    assert parsed[item][0].expired == 120.

    with pytest.raises(MKCounterWrapped):
        CheckResult(check.run_check(item, {}, parsed))
