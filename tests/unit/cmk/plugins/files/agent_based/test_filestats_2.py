#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.agent_based.v2 import Result, Service
from cmk.plugins.files.agent_based.filestats import (
    check_filestats,
    discover_filestats,
    parse_filestats,
)


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
    assert discovery[0] == Service(item="foo")


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

    # Filter to only Result objects for text-based assertions
    result_objects = [r for r in results if isinstance(r, Result)]

    # Should report file counts, size violations, and detailed file listing
    assert len(results) >= 6
    assert "Files in total: 5" in result_objects[0].summary
    assert "Smallest: 0 B" in result_objects[1].summary
    assert "Largest:" in result_objects[2].summary and "warn/crit" in result_objects[2].summary
    assert "Newest:" in result_objects[3].summary
    assert "Oldest:" in result_objects[4].summary
    # File details are now in a notice field
    detail_results = [r for r in result_objects if r.details and "/var/log/syslog.1" in r.details]
    assert len(detail_results) >= 1
