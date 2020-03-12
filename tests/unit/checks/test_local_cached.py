import pytest  # type: ignore[import]
from checktestlib import CheckResult, assertCheckResultsEqual

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
    assert parsed[item][0].cached == (420.0, 140.0, 300.0)

    result = CheckResult(check.run_check(item, {}, parsed))
    expected = CheckResult([
        (0, "On node node_1: This Check is outdated", [("V", 1.0)]),
        (0, "Cache generated 7 m ago, cache interval: 5 m, elapsed cache lifespan: 140%"),
    ])
    assertCheckResultsEqual(result, expected)
