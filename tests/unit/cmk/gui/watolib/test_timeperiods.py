#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.watolib.timeperiods import timeperiod_usage_finder_registry


def test_group_usage_finder_registry_entries() -> None:
    registered = [f.__name__ for f in timeperiod_usage_finder_registry.values()]
    assert sorted(registered) == sorted([])
