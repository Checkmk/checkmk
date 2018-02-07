import pytest
import pprint
from cmk_base.check_api import MKCounterWrapped
import checktestlib

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("time_to_info,params,predicate", [
(lambda t: [["cpu", 15*t, 10*t, 5*t, 5*t, 5*t, 5*t, 5*t]], {}, lambda cr: True),
])
def test_kernel_util_check(check_manager, time_to_info, params, predicate):
    check = check_manager.get_check("kernel.util")
    try:
        list(check.run_check(None, params, time_to_info(0)))
    except MKCounterWrapped:
        pass
    result = checktestlib.CheckResult(check.run_check(None, params, time_to_info(60)))
    assert predicate(result)
