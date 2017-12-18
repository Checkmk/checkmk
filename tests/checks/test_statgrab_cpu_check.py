import pytest
import pprint
from cmk_base.check_api import MKCounterWrapped
import checktestlib

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("time_to_info,params,expected_result", [
(lambda t: [[u'ctxsw', u'%d' % int(t*50)],
                   [u'idle', u'%d' % int(t*50)],
                   [u'intrs', u'%d' % int(t*50)],
                   [u'iowait', u'%d' % int(t*50)],
                   [u'kernel', u'%d' % int(t*50)],
                   [u'nice', u'%d' % int(t*50)],
                   [u'nvctxsw', u'%d' % int(t*50)],
                   [u'softintrs', u'%d' % int(t*50)],
                   [u'swap', u'%d' % int(t*50)],
                   [u'syscalls', u'%d' % int(t*50)],
                   [u'systime', u'%d' % int(t*50)],
                   [u'total', u'%d' % int(t*50)],
                   [u'user', u'%d' % int(t*50)],
                   [u'vctxsw', u'%d' % int(t*50)]],
            {}, None),
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
