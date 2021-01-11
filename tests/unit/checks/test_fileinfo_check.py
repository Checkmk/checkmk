import pytest

from collections import namedtuple
from testlib import Check  # type: ignore[import]
from checktestlib import (
    CheckResult,
    BasicCheckResult,
    PerfValue,
    assertCheckResultsEqual,
)

pytestmark = pytest.mark.checks

FileinfoItem = namedtuple("FileinfoItem", "name missing failed size time")


@pytest.mark.usefixtures("config_load_all_checks")
def test_fileinfo_min_max_age_levels():
    # This test has the following purpose:
    # For each file attr (size or age) the levels 'min*', 'max*' are evaluated.
    # 'min*' is evaluated first and if 'max*' returns state '0' (eg. not set)
    # the service state is also '0'.

    check = Check("fileinfo")
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

    # In 1.6.0 warn, crit of minage was added, but now we use the
    # generic check_levels function.
    assertCheckResultsEqual(
        CheckResult(output_minage),
        CheckResult([
            size_result,
            BasicCheckResult(
                1,
                "Age: 3.00 s (warn/crit below 5.00 s/1.00 s)",
                [
                    PerfValue('age', 3, None, None, None, None),
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
    # In 1.6.0 levels text of minage was added, but now we use the
    # generic check_levels function.
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
                "Age: 3.00 s (warn/crit at 1.00 s/2.00 s)",
                [
                    PerfValue('age', 3, 1, 2, None, None),
                ],
            ),
        ]))


@pytest.mark.parametrize(
    'info, parsed, expected_result',
    [
        (
            [
                # legacy format
                [u"1563288717"],
                [u"[[[header]]]"],
                [u"name", u"status", u"size", u"time"],
            ],
            {
                'reftime': 1563288717,
                'files': {},
            },
            [
                (0, 'Count: 0', [('count', 0, None, None)]),
                (0, 'Size: 0 B', [('size', 0, None, None)]),
                (0, '\nInclude patterns: /banana/*'),
            ],
        ),
        (
            [],
            {},
            [
                (3, 'Missing reference timestamp'),
            ],
        ),
        (
            [
                [u"1563288717"],
            ],
            {
                'reftime': 1563288717,
                'files': {},
            },
            [
                (0, 'Count: 0', [('count', 0, None, None)]),
                (0, 'Size: 0 B', [('size', 0, None, None)]),
                (0, '\nInclude patterns: /banana/*'),
            ],
        ),
    ])
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_fileinfo_group_no_files(info, parsed, expected_result):
    '''Test that the check returns an OK status when there are no files.'''

    fileinfo_groups_check = Check('fileinfo.groups')
    fileinfo_single_check = Check('fileinfo')
    assert fileinfo_single_check.run_parse(info) == parsed
    assert not fileinfo_groups_check.run_discovery(parsed)
    assert expected_result == list(
        fileinfo_groups_check.run_check(
            'banana',
            {'group_patterns': [('/banana/*', '')]},
            parsed,
        ))


@pytest.mark.parametrize(
    'info, parsed, expected_result',
    [
        (
            [
                # legacy format
                [u"1563288717"],
                [u"[[[header]]]"],
                [u"name", u"status", u"size", u"time"],
                [u"[[[content]]]"],
                [u'/bar/foo', 'ok', '384', '1465079135'],
                [u'/foo/bar', 'ok', '384', '1465079135'],
            ],
            {
                'reftime': 1563288717,
                'files': {
                    '/bar/foo': FileinfoItem(
                        name='/bar/foo', missing=False, failed=False, size=348, time=1465079135),
                    '/foo/bar': FileinfoItem(
                        name='/foo/bar', missing=False, failed=False, size=348, time=1465079135),
                }
            },
            [
                (0, 'Count: 0', [('count', 0, None, None)]),
                (0, 'Size: 0 B', [('size', 0, None, None)]),
                (0, '\nInclude patterns: /banana/*'),
            ],
        ),
        (
            [
                [u"1563288717"],
                [u'/bar/foo', '384', '1465079135'],
                [u'/foo/bar', '384', '1465079135'],
            ],
            {
                'reftime': 1563288717,
                'files': {
                    '/bar/foo': FileinfoItem(
                        name='/bar/foo', missing=False, failed=False, size=348, time=1465079135),
                    '/foo/bar': FileinfoItem(
                        name='/foo/bar', missing=False, failed=False, size=348, time=1465079135),
                }
            },
            [
                (0, 'Count: 0', [('count', 0, None, None)]),
                (0, 'Size: 0 B', [('size', 0, None, None)]),
                (0, '\nInclude patterns: /banana/*'),
            ],
        ),
    ])
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_fileinfo_group_no_matching_files(info, parsed, expected_result):
    '''Test that the check returns an OK status if there are no matching files.'''

    fileinfo_groups_check = Check('fileinfo.groups')
    fileinfo_single_check = Check('fileinfo')
    actual_parsed = fileinfo_single_check.run_parse(info)
    assert parsed['reftime'] == actual_parsed['reftime']
    assert list(parsed['files']) == list(actual_parsed['files'])
    assert expected_result == list(
        fileinfo_groups_check.run_check(
            'banana',
            {'group_patterns': [('/banana/*', '')]},
            parsed,
        ))


@pytest.mark.parametrize(
    'info, group_pattern, expected_result',
    [
        (
            [
                [u"1563288717"],
                [u'/var/log/syslog', '384', '1465079135'],
                [u'/var/log/syslog1', '384', '1465079135'],
            ],
            {
                # current format
                'group_patterns': [('/var/log/sys*', '')]
            },
            [
                (0, 'Count: 2', [('count', 2, None, None)]),
                (0, 'Size: 768 B', [('size', 768, None, None)]),
                (0, 'Largest size: 384 B', [('size_largest', 384, None, None)]),
                (0, 'Smallest size: 384 B', [('size_smallest', 384, None, None)]),
                (0, 'Oldest age: 3.1 y', [('age_oldest', 98209582, None, None)]),
                (0, 'Newest age: 3.1 y', [('age_newest', 98209582, None, None)]),
                (0, '\nInclude patterns: /var/log/sys*' \
                    '\n[/var/log/syslog] Age: 3.1 y, Size: 384 B' \
                    '\n[/var/log/syslog1] Age: 3.1 y, Size: 384 B'),
            ],
        ),
        (
            [
                [u"1563288717"],
                [u'/var/log/syslog', '384', '1465079135'],
                [u'/var/log/syslog1', '384', '1465079135'],
            ],
            {
                # legacy format
                'group_patterns': ['/var/log/sys*']
            },
            [(0, 'Count: 2', [('count', 2, None, None)]),
             (0, 'Size: 768 B', [('size', 768, None, None)]),
             (0, 'Largest size: 384 B', [('size_largest', 384, None, None)]),
             (0, 'Smallest size: 384 B', [('size_smallest', 384, None, None)]),
             (0, 'Oldest age: 3.1 y', [('age_oldest', 98209582, None, None)]),
             (0, 'Newest age: 3.1 y', [('age_newest', 98209582, None, None)]),
             (0, '\nInclude patterns: /var/log/sys*' \
                 '\n[/var/log/syslog] Age: 3.1 y, Size: 384 B' \
                 '\n[/var/log/syslog1] Age: 3.1 y, Size: 384 B'),
             ],
        ),
        (
            [
                [u"1563288717"],
                [u'/var/log/syslog', '384', '1465079135'],
                [u'/var/log/syslog1', '384', '1465079135'],
            ],
            {},
            [
             (3, "No group pattern found."),
            ],
        ),
        (
            [
                [u"1563288717"],
            ],
            {},
            [
             (3, "No group pattern found."),
            ],
        ),
        (
            [
                [u"1563288717"],
                [u'/var/log/syslog', '384', '1465079135'],
                [u'/var/log/syslog1', '384', '1465079135'],
            ],
            {
                # current format
                'group_patterns': [('/var/log/sys*', '/var/log/syslog1')]
            },
            [
                (0, 'Count: 1', [('count', 1, None, None)]),
                (0, 'Size: 384 B', [('size', 384, None, None)]),
                (0, 'Largest size: 384 B', [('size_largest', 384, None, None)]),
                (0, 'Smallest size: 384 B', [('size_smallest', 384, None, None)]),
                (0, 'Oldest age: 3.1 y', [('age_oldest', 98209582, None, None)]),
                (0, 'Newest age: 3.1 y', [('age_newest', 98209582, None, None)]),
                (0, '\nInclude patterns: /var/log/sys*' \
                    '\nExclude patterns: /var/log/syslog1' \
                    '\n[/var/log/syslog] Age: 3.1 y, Size: 384 B'),
            ],
        ),
    ])
def test_check_fileinfo_group_patterns(info, group_pattern, expected_result):
    fileinfo_groups_check = Check('fileinfo.groups')
    fileinfo_single_check = Check('fileinfo')
    assert expected_result == list(
        fileinfo_groups_check.run_check(
            'banana',
            group_pattern,
            fileinfo_single_check.run_parse(info),
        ))
