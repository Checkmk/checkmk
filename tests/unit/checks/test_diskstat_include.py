import re
import os
import pytest

from checktestlib import CheckResult, assertCheckResultsEqual

from cmk_base.check_api import get_bytes_human_readable, check_levels
pytestmark = pytest.mark.checks


def get_rate(_counter, _time, value):
    return value


def get_average(_counter, _time, value, _time_span):
    return round(value / 10.) * 10.


execfile(os.path.join(os.path.dirname(__file__), '../../../checks/diskstat.include'))


@pytest.mark.parametrize('args,expected_result', [
    ((1, '', {}, [None, None, 101, 201]),
     CheckResult((0, '50.50 kB/sec read, 0.00 MB/s, 100.50 kB/sec write, 0.00 MB/s', [
         ('read', 51712),
         ('write', 102912),
     ]))),
    ((1, '', {
        'average': 1
    }, [None, None, 101, 201]),
     CheckResult((0, '50.50 kB/sec read, 0.05 MB/s, 100.50 kB/sec write, 0.10 MB/s', [
         ('read', 51712),
         ('write', 102912),
         ('read.avg', 51710.0),
         ('write.avg', 102910.0),
     ]))),
])
def test_check_diskstat_line(args, expected_result):
    actual_result = CheckResult(check_diskstat_line(*args))
    assertCheckResultsEqual(actual_result, expected_result)
