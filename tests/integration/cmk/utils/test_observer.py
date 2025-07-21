#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Consolidate tests which validate the interface between Checkmk and `proc`."""

from tests.testlib.site import Site


def test_access_to_proc(site: Site) -> None:
    """Validate site has access to file `/proc/self/statm`."""
    FILE_PATH = "/proc/self/statm"
    assert site.read_file(FILE_PATH), f"site: '{site.id}' cannot access '{FILE_PATH}'!"
