import pytest
from cmk_base.check_api import MKCounterWrapped
from checktestlib import CheckResult, assertCheckResultsEqual, BasicCheckResult

pytestmark = pytest.mark.checks


def cpu_info(t):
    return [
        ["cpu", 10 * t, 4 * t, 6 * t, 8 * t, 5 * t, 8 * t, 3 * t, 6 * t, 2 * t, 4 * t],
        ["cpu0", 6 * t, 3 * t, 3 * t, 2 * t, 3 * t, 3 * t, 1 * t, 5 * t, 1 * t, 2 * t],
        ["cpu1", 4 * t, 1 * t, 3 * t, 6 * t, 2 * t, 5 * t, 2 * t, 1 * t, 1 * t, 2 * t],
    ]


def reference_result(deviation):
    reference = [
        (0, 'user: 16.0%, system: 34.0%', [('user', 16.0, None, None, None, None),
                                           ('system', 34.0, None, None, None, None),
                                           ('wait', 10.0, None, None, None, None)]),
        (0, 'wait: 10.0%', None),
        (0, 'steal: 12.0%', [('steal', 12.0, None, None, None, None)]),
        (0, 'guest: 12.0%', [('guest', 12.0, None, None, None, None)]),
        (0, 'total: 84.0%', None),
    ]
    if isinstance(deviation, tuple):
        reference[deviation[0]] = deviation[1]
    if callable(deviation):
        deviation(reference)

    return reference


@pytest.mark.parametrize("params, change", [
    ({
        'levels_single': (20.0, 55.0)
    }, lambda x: x.extend([(2, 'Core cpu0: 96.0% (warn/crit at 20.0%/55.0%)', []), (2, 'Core cpu1: 72.0% (warn/crit at 20.0%/55.0%)', [])])),
    ({}, None),
    ({
        'iowait': (5, 6)
    }, (1, (2, 'wait: 10.0%', None))),
    ({
        'core_util_time_total': (100.0, 300, 900)
    }, None),
])
def test_kernel_util_check(check_manager, params, change):
    check = check_manager.get_check("kernel.util")
    assert check.run_discovery(cpu_info(0)) == [(None, {})]
    try:
        list(check.run_check(None, params, cpu_info(0)))
    except MKCounterWrapped:
        pass
    result = CheckResult(check.run_check(None, params, cpu_info(10)))

    reference = CheckResult([BasicCheckResult(*x) for x in reference_result(change)])

    assertCheckResultsEqual(result, reference)
