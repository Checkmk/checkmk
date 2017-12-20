import pytest
import pprint
from cmk_base.check_api import MKCounterWrapped
import checktestlib

pytestmark = pytest.mark.checks


info_statgrab_cpu_hpux = lambda t: [[u'idle', u'%d' % int(t*5)],
                                    [u'iowait', u'%d' % int(t*10)],
                                    [u'kernel', u'%d' % int(t*10)],
                                    [u'nice', u'%d' % int(t*20)],
                                    [u'swap', u'0'],
                                    [u'systime', u'%d' % int(t*25)],
                                    [u'total', u'%d' % int(t*100)],
                                    [u'user', u'%d' % int(t*30)]]

@pytest.mark.parametrize("time_to_info,params,expected_result", [
(info_statgrab_cpu_hpux, {}, {}),
])
def test_statgrab_cpu_check(check_manager, monkeypatch, time_to_info, params, expected_result):
    import time
    check = check_manager.get_check("statgrab_cpu")
    try:
        list(check.run_check(None, params, time_to_info(0)))
    except MKCounterWrapped:
        pass
    monkeypatch.setattr("time.time", lambda: 60)
    result = checktestlib.CompoundCheckResult(check.run_check(None, params, time_to_info(60)))
