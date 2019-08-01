import pytest
from cmk_base.check_api import MKCounterWrapped
from checktestlib import CheckResult, assertCheckResultsEqual

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("data, result", [
    (("cpu5", 2), "cpu_core_util_5"),
    (("cpu65", 35), "cpu_core_util_65"),
    (("cpuaex", 15), "cpu_core_util_15"),
])
def test_cpu_util_core_name(check_manager, data, result):
    check = check_manager.get_check("kernel.util")
    assert check.context["cpu_util_core_name"](*data) == result


def cpu_info(t):
    return [
        ["cpu", 10 * t, 4 * t, 6 * t, 8 * t, 5 * t, 8 * t, 3 * t, 6 * t, 2 * t, 4 * t],
        ["cpu-a", 6 * t, 3 * t, 3 * t, 2 * t, 3 * t, 3 * t, 1 * t, 5 * t, 1 * t, 2 * t],
        ["cpu-b", 4 * t, 1 * t, 3 * t, 6 * t, 2 * t, 5 * t, 2 * t, 1 * t, 1 * t, 2 * t],
    ]


def reference_result(deviation):
    reference = [
        (0, 'User: 16.0%', [('user', 16.0, None, None, None, None)]),
        (0, 'System: 34.0%', [('system', 34.0, None, None, None, None)]),
        (0, 'Wait: 10.0%', [('wait', 10.0, None, None, None, None)]),
        (0, 'Steal: 12.0%', [('steal', 12.0, None, None, None, None)]),
        (0, 'Guest: 12.0%', [('guest', 12.0, None, None, None, None)]),
        (0, 'Total CPU: 84.0%', [('util', 84.0, None, None, 0, None)]),
    ]
    if isinstance(deviation, tuple):
        reference[deviation[0]] = deviation[1]
    if hasattr(deviation, '__call__'):
        deviation(reference)

    return reference


@pytest.mark.parametrize("params, change", [
    ({
        'levels_single': (70.0, 90.0)
    }, lambda x: x.extend([(2, 'Core cpu-a: 96.0% (warn/crit at 70.0%/90.0%)', []),
                           (1, 'Core cpu-b: 72.0% (warn/crit at 70.0%/90.0%)', [])])),
    ({}, None),
    ({
        'iowait': (5, 6)
    }, (2, (2, 'Wait: 10.0% (warn/crit at 5.0%/6.0%)', [('wait', 10.0, 5.0, 6.0, None, None)]))),
    ({
        'core_util_graph': True
    }, lambda x: x.extend([(0, '', [('cpu_core_util_0', 96.0)]),
                           (0, '', [('cpu_core_util_1', 72.0)])])),
    ({
        'core_util_time_total': (100.0, 300, 900)
    }, lambda x: x.append((0, '', []))),
    ({
        'core_util_time': (70.0, 5, 20)
    }, lambda x: x.extend([
        (1, 'cpu-a is under high load for: 10.0 s (warn/crit at 5.00 s/20.0 s)', []),
        (1, 'cpu-b is under high load for: 10.0 s (warn/crit at 5.00 s/20.0 s)', []),
    ])),
])
def test_kernel_util_check(check_manager, monkeypatch, params, change):
    check = check_manager.get_check("kernel.util")
    assert check.run_discovery(cpu_info(0)) == [(None, {})]

    monkeypatch.setattr('time.time', lambda: 0)
    try:
        list(check.run_check(None, params, cpu_info(0)))
    except MKCounterWrapped:
        pass
    # second pass
    monkeypatch.setattr('time.time', lambda: 10)
    list(check.run_check(None, params, cpu_info(10)))

    monkeypatch.setattr('time.time', lambda: 20)
    result = CheckResult(check.run_check(None, params, cpu_info(20)))

    reference = CheckResult(reference_result(change))

    assertCheckResultsEqual(result, reference)
