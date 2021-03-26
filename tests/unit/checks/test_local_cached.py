import pytest  # type: ignore[import]
from checktestlib import CheckResult, assertCheckResultsEqual
from cmk.utils.exceptions import MKGeneralException

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('info,exception_reason', [
    (
        [['node_1', 'cached(1556005301,300)', 'foo']],
        ("Invalid line in agent section <<<local>>>. "
         "Reason: Received wrong format of local check output. "
         "Please read the documentation regarding the correct format: "
         "https://docs.checkmk.com/1.6.0/de/localchecks.html  "
         "Received output: \"foo\""),
    ),
    (
        [['node_1', 'cached(1556005301,300)']],
        ("Invalid line in agent section <<<local>>>. Reason: Received empty line. "
         "Did any of your local checks returned a superfluous newline character? "
         "Received output: \"\""),
    ),
])
def test_local_format_error(check_manager, info, exception_reason):
    check = check_manager.get_check('local')

    with pytest.raises(MKGeneralException) as e:
        check.run_discovery(check.run_parse(info))
    assert str(e.value) == exception_reason


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
