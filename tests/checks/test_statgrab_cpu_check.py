import pytest
import pprint
from cmk_base.check_api import MKCounterWrapped

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("timepoints,time_to_info,params,expected_results", [
([60],lambda t: [[u'ctxsw', u'%d' % int(t*50)],
                   [u'idle', int(t*50)],
                   [u'intrs',int(t*50)],
                   [u'iowait',int(t*50)],
                   [u'kernel',int(t*50)],
                   [u'nice',int(t*50)],
                   [u'nvctxsw',int(t*50)],
                   [u'softintrs',int(t*50)],
                   [u'swap',int(t*50)],
                   [u'syscalls',int(t*50)],
                   [u'systime',int(t*50)],
                   [u'total',int(t*50)],
                   [u'user',int(t*50)],
                   [u'vctxsw',int(t*50)]],
            {}, None),
])
def test_statgrab_cpu_check(check_manager, monkeypatch, timepoints, time_to_info, params, expected_results):
    import time
    check = check_manager.get_check("statgrab_cpu")
    try:
        result = list(check.run_check(None, params, time_to_info(0)))
    except MKCounterWrapped:
        pass
    for t in timepoints:
        monkeypatch.setattr("time.time", lambda: t)
        result = list(check.run_check(None, params, time_to_info(t)))
