import pytest  # type: ignore
from testlib import on_time
from checktestlib import CheckResult, assertCheckResultsEqual

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


@pytest.mark.parametrize("string, result", [
    ('22 day(s),  8:46', 1932360),
    ('4 day(s),  3 hr(s)', 356400),
    ('76 day(s), 26 min(s)', 6567960),
    ('1086 day(s)', 93830400),
    ('5 min(s)', 300),
    ('2 hr(s)', 7200),
])
def test_human_read_uptime(check_manager, string, result):
    check = check_manager.get_check("uptime")
    assert check.context['parse_human_read_uptime'](string) == result


@pytest.mark.parametrize(
    "info,result",
    [
        # Discover the service once non-empty agent output is available
        ([], None),
        ([[]], [(None, {})]),
    ])
def test_uptime_discovery2(check_manager, info, result):
    check = check_manager.get_check("uptime")
    assert check.run_discovery(info) == result


def test_uptime_check_basic(check_manager):
    check = check_manager.get_check("uptime")

    parsed = check.run_parse([["123"]])
    result = next(check.run_check(None, {}, parsed))
    assert len(result) == 3
    assert result[0] == 0
    assert "Up since " in result[1]
    assert result[2] == [("uptime", 123.0, None, None)]


def test_uptime_check_zero(check_manager):
    check = check_manager.get_check("uptime")

    parsed = check.run_parse([["0"]])
    result = next(check.run_check(None, {}, parsed))
    assert len(result) == 3
    assert result[0] == 0
    assert "Up since " in result[1]
    assert result[2] == [("uptime", 0.0, None, None)]


@pytest.mark.parametrize('info, reference', [
    ([[u'22731'], [u'[uptime_solaris_start]'],
      [u'SunOS', u'unknown', u'5.10', u'Generic_147148-26', u'i86pc', u'i386', u'i86pc'],
      [u'global'],
      [
          u'4:58pm', u'up', u'6:19,', u'2', u'users,', u'load', u'average:', u'0.18,', u'0.06,',
          u'0.03'
      ], [u'unix:0:system_misc:snaptime', u'22737.886916295'], [u'[uptime_solaris_end]']],
     (0, 'Up since Sun Apr 15 12:31:09 2018, uptime: 6:18:51', [('uptime', 22731)])),
    ([[u'1122'], [u'[uptime_solaris_start]'],
      [u'SunOS', u'unknown', u'5.10', u'Generic_147148-26', u'i86pc', u'i386', u'i86pc'],
      [u'global'],
      [
          u'4:23pm', u'up', u'19', u'min(s),', u'2', u'users,', u'load', u'average:', u'0.03,',
          u'0.09,', u'0.09'
      ], [u'unix:0:system_misc:snaptime', u'1131.467157594'], [u'[uptime_solaris_end]']],
     (0, 'Up since Sun Apr 15 18:31:18 2018, uptime: 0:18:42', [('uptime', 1122)])),
    ([[u'1553086171'], [u'[uptime_solaris_start]'], [u'SunOS', u'Solaris', u'11.3', u'X86'],
      [u'non-global', u'zone'],
      [
          u'1:53pm', u'up', u'335', u'day(s),', u'23:13,', u'0', u'users,', u'load', u'average:',
          u'0.36,', u'0.34,', u'0.34'
      ], [u'unix:0:system_misc:snaptime', u'29027808.0471184'], [u'[uptime_solaris_end]']],
     (0, 'Up since Sun May 14 19:33:11 2017, uptime: 335 days, 23:16:48', [
         ('uptime', 29027808.0471184)
     ])),
    ([[u'54043590'], [u'[uptime_solaris_start]'],
      [u'SunOS', u'sveqdcmk01', u'5.10', u'Generic_150401-49', u'i86pc', u'i386', u'i86pc'],
      [u'sveqdcmk01'],
      [
          u'1:50pm', u'up', u'420', u'day(s),', u'21:05,', u'43', u'users,', u'load', u'average:',
          u'16.75,', u'19.66,', u'18.18'
      ], [u'unix:0:system_misc:snaptime', u'54048049.7479652'], [u'[uptime_solaris_end]']],
     (3, 'Your Solaris system gives inconsistent uptime information. Please get it fixed. Uptime '
      'command: 420 days, 21:05:00; Kernel time since boot: 625 days, 12:06:30; Snaptime: 625 days, 13:20:49.747965'
     )),
    ([[u'1529194584'], [u'[uptime_solaris_start]'],
      [u'SunOS', u'sc000338', u'5.10', u'Generic_150400-61', u'sun4v', u'sparc', u'SUNW'],
      [u'sc000338'],
      [
          u'1:50pm', u'up', u'282', u'day(s),', u'13:40,', u'1', u'user,', u'load', u'average:',
          u'3.38,', u'3.44,', u'3.49'
      ], [u'unix:0:system_misc:snaptime', u'70236854.9797181'], [u'[uptime_solaris_end]']],
     (3, 'Your Solaris system gives inconsistent uptime information. Please get it fixed. Uptime '
      'command: 282 days, 13:40:00; Kernel time since boot: 17699 days, 0:16:24; Snaptime: 812 days, 22:14:14.979718'
     ))
])
def test_uptime_solaris_inputs(check_manager, info, reference):
    check = check_manager.get_check("uptime")

    parsed = check.run_parse(info)

    # This time freeze has no correlation with the uptime of the test. It
    # is needed for the check output to always return the same infotext.
    # The true test happens on state and perfdata
    with on_time('2018-04-15 16:50', 'CET'):
        result = CheckResult(check.run_check(None, {}, parsed))
    assertCheckResultsEqual(result, CheckResult(reference))
