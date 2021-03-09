import pytest

from checktestlib import (
    CheckResult,
    BasicCheckResult,
    PerfValue,
    assertCheckResultsEqual,
)

pytestmark = pytest.mark.checks


def test_fileinfo_min_max_age_levels(check_manager):
    # This test has the following purpose:
    # For each file attr (size or age) the levels 'min*', 'max*' are evaluated.
    # 'min*' is evaluated first and if 'max*' returns state '0' (eg. not set)
    # the service state is also '0'.

    check = check_manager.get_check("fileinfo")
    item = u'c:\\filetest\\check_mk.txt'
    parsed = check.run_parse([
        [u'8'],
        [u'c:\\filetest\\check_mk.txt', u'7', u'5'],
    ])

    size_result = BasicCheckResult(
        0,
        "Size: 7 B",
        [
            PerfValue('size', 7, None, None, None, None),
        ],
    )

    # minage matches
    output_minage = check.run_check(item, {
        'minage': (5, 1),
    }, parsed)

    assertCheckResultsEqual(
        CheckResult(output_minage),
        CheckResult([
            size_result,
            BasicCheckResult(
                1,
                "Age: 3.00 s (warn/crit below 5.00 s/1.00 s)",
                [
                    PerfValue('age', 3, 5, 1, None, None),
                ],
            ),
        ]))

    # maxage matches
    output_maxage = check.run_check(item, {
        'maxage': (1, 2),
    }, parsed)

    assertCheckResultsEqual(
        CheckResult(output_maxage),
        CheckResult([
            size_result,
            BasicCheckResult(
                2,
                "Age: 3.00 s (warn/crit at 1.00 s/2.00 s)",
                [
                    PerfValue('age', 3, 1, 2, None, None),
                ],
            ),
        ]))

    # both match
    # This should never happen (misconfiguration), but test the order
    # of min* vs. max* and perfdata (always take the upper levels)
    output_both = check.run_check(item, {
        'minage': (5, 1),
        'maxage': (1, 2),
    }, parsed)

    assertCheckResultsEqual(
        CheckResult(output_both),
        CheckResult([
            size_result,
            BasicCheckResult(
                2,
                "Age: 3.00 s (warn/crit below 5.00 s/1.00 s) (warn/crit at 1.00 s/2.00 s)",
                [
                    PerfValue('age', 3, 1, 2, None, None),
                ],
            ),
        ]))
