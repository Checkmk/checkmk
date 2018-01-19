import pytest
import pprint
from cmk_base.check_api import MKCounterWrapped
import checktestlib

pytestmark = pytest.mark.checks


info_statgrab_cpu_hpux = lambda t: [[u'idle', u'%d' % int(t*5)],
                                    [u'iowait', u'%d' % int(t*5)],
                                    [u'kernel', u'%d' % int(t*5)],
                                    [u'nice', u'%d' % int(t*5)],
                                    [u'swap', u'0'],
                                    [u'systime', u'%d' % int(t*5)],
                                    [u'total', u'%d' % int(t*30)],
                                    [u'user', u'%d' % int(t*5)]]

@pytest.mark.parametrize("time_to_info,params,predicate", [
(info_statgrab_cpu_hpux, {}, lambda cr: ("user", 40.0) in cr.perfdata and       # TODO: This only represents the status quo - check whether this even makes sense.
                                        ("system", 20.0) in cr.perfdata and     #       Note that systime and total are being ignored entirely by the check.
                                        ("wait", 20.0) in cr.perfdata
    ),
])
def test_statgrab_cpu_check(check_manager, monkeypatch, time_to_info, params, predicate):
    import time
    check = check_manager.get_check("statgrab_cpu")
    try:
        list(check.run_check(None, params, time_to_info(0)))
    except MKCounterWrapped:
        pass
    monkeypatch.setattr("time.time", lambda: 60)
    result = checktestlib.CheckResult(check.run_check(None, params, time_to_info(60)))
    assert predicate(result)
