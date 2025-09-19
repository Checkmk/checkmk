#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.base.legacy_checks.filestats import check_filestats, discover_filestats, parse_filestats


def test_filestats_2_discovery():
    """Test discovery of file statistics."""
    # Pattern 5d: System monitoring data (file statistics from agent)
    string_table = [
        ["[[[file_stats foo]]]"],
        [
            "{'age': 21374, 'mtime': 1600757875, 'path': '/var/log/boot.log', 'size': 0, 'stat_status': 'ok', 'type': 'file'}"
        ],
        [
            "{'stat_status': 'ok', 'age': 0, 'mtime': 160779533, 'path': '/var/log/syslog', 'type': 'file', 'size': 13874994}"
        ],
        [
            "{'stat_status': 'ok', 'age': 4079566, 'mtime': 1596699967, 'path': '/var/log/syslog.3.gz', 'type': 'file', 'size': 5313033}"
        ],
        [
            "{'stat_status': 'ok', 'age': 1661230, 'mtime': 1599118303, 'path': '/var/log/syslog.1', 'type': 'file', 'size': 22121937}"
        ],
        [
            "{'stat_status': 'ok', 'age': 4583773, 'mtime': 1596195760, 'path': '/var/log/apport.log.2.gz', 'type': 'file', 'size': 479}"
        ],
        ["{'type': 'summary', 'count': 5}"],
    ]

    # Test discovery
    parsed = parse_filestats(string_table)
    discovery = list(discover_filestats(parsed))
    assert len(discovery) == 1
    assert discovery[0][0] == "foo"


def test_filestats_2_check():
    """Test file statistics check with size threshold violations."""
    # Pattern 5d: System monitoring data
    string_table = [
        ["[[[file_stats foo]]]"],
        [
            "{'age': 21374, 'mtime': 1600757875, 'path': '/var/log/boot.log', 'size': 0, 'stat_status': 'ok', 'type': 'file'}"
        ],
        [
            "{'stat_status': 'ok', 'age': 0, 'mtime': 160779533, 'path': '/var/log/syslog', 'type': 'file', 'size': 13874994}"
        ],
        [
            "{'stat_status': 'ok', 'age': 4079566, 'mtime': 1596699967, 'path': '/var/log/syslog.3.gz', 'type': 'file', 'size': 5313033}"
        ],
        [
            "{'stat_status': 'ok', 'age': 1661230, 'mtime': 1599118303, 'path': '/var/log/syslog.1', 'type': 'file', 'size': 22121937}"
        ],
        [
            "{'stat_status': 'ok', 'age': 4583773, 'mtime': 1596195760, 'path': '/var/log/apport.log.2.gz', 'type': 'file', 'size': 479}"
        ],
        ["{'type': 'summary', 'count': 5}"],
    ]

    params = {"maxsize_largest": (1, 2), "show_all_files": True}

    parsed = parse_filestats(string_table)
    results = list(check_filestats("foo", params, parsed))

    # Should report file counts, size violations, and detailed file listing
    assert len(results) >= 6
    assert "Files in total: 5" in results[0][1]
    assert "Smallest: 0 B" in results[1][1]
    assert "Largest:" in results[2][1] and "warn/crit" in results[2][1]
    assert "Newest:" in results[3][1]
    assert "Oldest:" in results[4][1]
    assert "/var/log/syslog.1" in results[5][1]  # File details
