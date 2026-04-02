#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.files.agent_based.filestats import (
    check_filestats,
    discover_filestats,
    parse_filestats,
)


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
    assert discovery[0] == Service(item="dtb")


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

    # Filter to Result objects for text-based assertions
    result_objects = [r for r in results if isinstance(r, Result)]

    # Should report critical file count violation and show all files
    assert len(results) >= 6
    assert "Files in total: 3" in result_objects[0].summary
    assert "warn/crit at 1/1" in result_objects[0].summary
    # File paths are now in the details field
    assert "/var/bla" in result_objects[0].details
    assert "/var/foo" in result_objects[0].details
    assert "/var/boo" in result_objects[0].details
    assert result_objects[0].state == State.CRIT
    assert "Smallest:" in result_objects[1].summary
    assert "Largest:" in result_objects[2].summary
