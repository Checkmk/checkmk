#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.base.legacy_checks.filestats import check_filestats, discover_filestats, parse_filestats


def test_filestats_display_files_count_discovery():
    """Test discovery of file statistics with file count display."""
    # Pattern 5d: System monitoring data (file statistics from agent)
    string_table = [
        ["[[[file_stats dtb]]]"],
        [
            "{'stat_status': 'ok', 'age': 13761362, 'mtime': 1642827699, 'path': u'/var/bla', 'type': 'file', 'size': 47736}"
        ],
        [
            "{'stat_status': 'ok', 'age': 13592155, 'mtime': 1642996906, 'path': u'/var/foo', 'type': 'file', 'size': 18954}"
        ],
        [
            "{'stat_status': 'ok', 'age': 13505726, 'mtime': 1643083335, 'path': u'/var/boo', 'type': 'file', 'size': 38610}"
        ],
        ["{'count': 3, 'type': 'summary'}"],
    ]

    # Test discovery
    parsed = parse_filestats(string_table)
    discovery = list(discover_filestats(parsed))
    assert len(discovery) == 1
    assert discovery[0][0] == "dtb"


def test_filestats_display_files_count_check():
    """Test file statistics check with file count threshold violations."""
    # Pattern 5d: System monitoring data
    string_table = [
        ["[[[file_stats dtb]]]"],
        [
            "{'stat_status': 'ok', 'age': 13761362, 'mtime': 1642827699, 'path': u'/var/bla', 'type': 'file', 'size': 47736}"
        ],
        [
            "{'stat_status': 'ok', 'age': 13592155, 'mtime': 1642996906, 'path': u'/var/foo', 'type': 'file', 'size': 18954}"
        ],
        [
            "{'stat_status': 'ok', 'age': 13505726, 'mtime': 1643083335, 'path': u'/var/boo', 'type': 'file', 'size': 38610}"
        ],
        ["{'count': 3, 'type': 'summary'}"],
    ]

    params = {"maxcount": (1, 1), "show_all_files": True}

    parsed = parse_filestats(string_table)
    results = list(check_filestats("dtb", params, parsed))

    # Should report critical file count violation and show all files
    assert len(results) >= 6
    assert "Files in total: 3" in results[0][1]
    assert "warn/crit at 1/1" in results[0][1]
    assert "/var/bla" in results[0][1]
    assert "/var/foo" in results[0][1]
    assert "/var/boo" in results[0][1]
    assert results[0][0] == 2  # Critical state
    assert "Smallest:" in results[1][1]
    assert "Largest:" in results[2][1]
