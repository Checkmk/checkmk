import pytest
from checktestlib import CheckResult, assertCheckResultsEqual, \
                         BasicItemState, MockItemState, assertMKCounterWrapped

pytestmark = pytest.mark.checks

info_statgrab_cpu_hpux = [
    [u'idle', u'300'],
    [u'iowait', u'300'],
    [u'kernel', u'300'],
    [u'nice', u'300'],
    [u'swap', u'0'],
    [u'systime', u'300'],
    [u'total', u'1800'],
    [u'user', u'300'],
]

# If mock_state is a tuple, it is returned upon
# every call to `get_item_state`. Let's say
# The check ran 23 seconds ago, and all values
# were zero:
mock_state_tuple = (23., 0)

# If mock_state is a dictionary, the values will
# be returned according to their key,
# as you would expect.
mock_state_dict = {
    'cpu.util.1': (3, 200),  # user
    'cpu.util.2': (1, 220),  # nice
    'cpu.util.3': (4, 100),  # system
    'cpu.util.4': (1, 123),  # idle
    'cpu.util.5': (5, 50),  # iowait
    'cpu.util.6': (9, 0),  # irq
    'cpu.util.7': (2, 0),  # softirq
    'cpu.util.8': (6, 0),  # steal
    'cpu.util.9': (5, 0),  # guest
    'cpu.util.10': (3, 0),  # guest_nice
}


# If mock_state is a function, it must accept two
# arguments, just like dict.get:
def mock_state_function(key, _default):
    counter = int(key.split('.')[-1])
    return (23, (counter < 6) * 300)


expected_result_1 = CheckResult([(0, 'User: 40.0%', [('user', 40.0, None, None, None, None)]),
                                 (0, 'System: 20.0%', [('system', 20.0, None, None, None, None)]),
                                 (0, 'Wait: 20.0%', [('wait', 20.0, None, None, None, None)]),
                                 (0, 'Total CPU: 80.0%', [('util', 80.0, None, None, 0, None)])])

expected_result_2 = CheckResult([
    (0, 'User: 22.3%', [('user', 22.304832713754646, None, None, None, None)]),
    (0, 'System: 24.78%', [('system', 24.783147459727385, None, None, None, None)]),
    (0, 'Wait: 30.98%', [('wait', 30.97893432465923, None, None, None, None)]),
    (0, 'Total CPU: 78.07%', [('util', 78.06691449814126, None, None, 0, None)])
])


@pytest.mark.parametrize("info,mockstate,expected_result", [
    (info_statgrab_cpu_hpux, mock_state_tuple, expected_result_1),
    (info_statgrab_cpu_hpux, mock_state_dict, expected_result_2),
])
def test_statgrab_cpu_check(check_manager, info, mockstate, expected_result):

    check = check_manager.get_check("statgrab_cpu")

    # set up mocking of `get_item_state`
    with MockItemState(mockstate):
        result = CheckResult(check.run_check(None, {}, info))
    assertCheckResultsEqual(result, expected_result)


@pytest.mark.parametrize("info,mockstate", [
    (info_statgrab_cpu_hpux, mock_state_function),
])
def test_statgrab_cpu_check_error(check_manager, info, mockstate):

    check = check_manager.get_check("statgrab_cpu")

    with MockItemState(mockstate):
        # the mock values are designed to raise an exception.
        # to make sure it is raised, use this:
        with assertMKCounterWrapped('Too short time difference since last check'):
            CheckResult(check.run_check(None, {}, info))
        # # You could omit the error message it you don't care about it:
        # with assertMKCounterWrapped()
        #     CheckResult(check.run_check(None, {}, info))
