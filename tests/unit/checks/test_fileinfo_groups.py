import pytest

from checktestlib import (
    CheckResult,
    BasicCheckResult,
    PerfValue,
    assertCheckResultsEqual,
)

pytestmark = pytest.mark.checks


def test_fileinfo_groups_no_files(check_manager):
    # This test has the following purpose:
    # For each file attr (size or age) the levels 'min*', 'max*' are evaluated.
    # 'min*' is evaluated first and if 'max*' returns state '0' (eg. not set)
    # the service state is also '0'.

    fileinfo_check = check_manager.get_check("fileinfo")
    fileinfo_groups_check = check_manager.get_check("fileinfo.groups")

    parsed = fileinfo_check.run_parse([
        [u'0'],
    ])
    result = fileinfo_groups_check.run_check("unused", {}, parsed)

    assertCheckResultsEqual(
        CheckResult(result),
        CheckResult([
            BasicCheckResult(
                0,
                "Count: 0",
                [
                    PerfValue('count', 0, None, None, None, None),
                ],
            ),
            BasicCheckResult(
                0,
                "Size: 0 B",
                [
                    PerfValue('size', 0, None, None, None, None),
                ],
            ),
        ]))
