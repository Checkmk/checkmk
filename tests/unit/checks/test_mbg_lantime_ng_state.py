import pytest  # type: ignore
from checktestlib import CheckResult, assertCheckResultsEqual

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    'params, result',
    [
        (
            {
                "stratum": (2, 3),
                "offset": (10, 20),  # us
            },
            (0, u'Reference clock offset: 0.9 \xb5s', [('offset', 0.9, 10, 20)])),
        (
            {
                "stratum": (2, 3),
                "offset": (0.9, 20),  # us
            },
            (1, u'Reference clock offset: 0.9 \xb5s (warn/crit at 0.9/20 \xb5s)', [
                ('offset', 0.9, 0.9, 20)
            ])),
        (
            {
                "stratum": (2, 3),
                "offset": (0.9, 0.9),  # us
            },
            (2, u'Reference clock offset: 0.9 \xb5s (warn/crit at 0.9/0.9 \xb5s)', [
                ('offset', 0.9, 0.9, 0.9)
            ])),
    ])
def test_mbg_lantime_ng_state_ref_clock(check_manager, params, result):
    check = check_manager.get_check('mbg_lantime_ng_state')
    ref_clock_result = list(check.run_check(None, params, [[u'2', u'1', u'GPS', u'0.0009']]))[-1]
    assert ref_clock_result == result
