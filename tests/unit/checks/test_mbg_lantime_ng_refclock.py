import pytest  # type: ignore
from checktestlib import DiscoveryResult, assertDiscoveryResultsEqual, \
                         BasicCheckResult, CheckResult, assertCheckResultsEqual

pytestmark = pytest.mark.checks

meinberg_lantime_1 = [[u'1', u'14', u'3', u'2', u'3', u'0', u'12', u'0', u'0', u'0', u'2012-06-30']]
meinberg_lantime_2 = [[u'1', u'28', u'3', u'1', u'52', u'62', u'100', u'101', u'127', u'0', u'0']]
meinberg_lantime_5 = [[
    u'1', u'14', u'3', u'1', u'150', u'6', u'8', u'0', u'0', u'1', u'not announced'
]]


@pytest.mark.parametrize(
    "info,expected",
    [
        (meinberg_lantime_1, DiscoveryResult([])),  # GPS clocks are not covered here
        (meinberg_lantime_2, DiscoveryResult([('1', None)])),
    ])
def test_discovery_mbg_lantime_ng_refclock(check_manager, info, expected):
    check = check_manager.get_check("mbg_lantime_ng_refclock")
    discovery = DiscoveryResult(check.run_discovery(info))
    assertDiscoveryResultsEqual(check, discovery, expected)


@pytest.mark.parametrize("info,item,params,expected", [
    (meinberg_lantime_2, '1', (3, 3),
     CheckResult([
         BasicCheckResult(0, 'Type: pzf600, Usage: primary, State: synchronized (LW sync)', None),
         BasicCheckResult(0, 'Field strength: 80%', [('field_strength', 80.0)]),
         BasicCheckResult(0, 'Correlation: 62%', [('correlation', 62.0)]),
     ])),
])
def test_check_mbg_lantime_ng_refclock(check_manager, info, item, params, expected):
    check = check_manager.get_check("mbg_lantime_ng_refclock")
    result = CheckResult(check.run_check(item, params, info))
    assertCheckResultsEqual(result, expected)


@pytest.mark.parametrize(
    "info,expected",
    [
        (meinberg_lantime_1, DiscoveryResult([('1', 'mbg_lantime_refclock_default_levels')])),
        (meinberg_lantime_2, DiscoveryResult([])),  # don't discover GPS clocks
        (meinberg_lantime_5, DiscoveryResult([('1', 'mbg_lantime_refclock_default_levels')])),
    ])
def test_discovery_mbg_lantime_ng_refclock_gps(check_manager, info, expected):
    check = check_manager.get_check("mbg_lantime_ng_refclock.gps")
    discovery = DiscoveryResult(check.run_discovery(info))
    assertDiscoveryResultsEqual(check, discovery, expected)


@pytest.mark.parametrize("info,item,params,expected", [
    (meinberg_lantime_1, '1', (3, 3),
     CheckResult([
         BasicCheckResult(
             1, 'Type: gps170, Usage: primary, State: not synchronized (GPS antenna disconnected)',
             None),
         BasicCheckResult(0, 'Next leap second: 2012-06-30', None),
         BasicCheckResult(2, 'Satellites: 0/12 (warn/crit below 3/3)', None)
     ])),
    (meinberg_lantime_5, '1', (3, 3),
     CheckResult([
         BasicCheckResult(0, 'Type: gps170, Usage: primary, State: synchronized (MRS GPS sync)',
                          None),
         BasicCheckResult(0, 'Next leap second: not announced', None),
         BasicCheckResult(0, 'Satellites: 6/8', None)
     ])),
])
def test_check_mbg_lantime_ng_refclock_gps(check_manager, info, item, params, expected):
    check = check_manager.get_check("mbg_lantime_ng_refclock.gps")
    result = CheckResult(check.run_check(item, params, info))
    assertCheckResultsEqual(result, expected)
