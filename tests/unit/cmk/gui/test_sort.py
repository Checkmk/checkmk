#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils.sort import natural_sort


def test_natural_sort() -> None:
    # Test if natural sort function complies with criteria requested (https://jira.lan.tribe29.com/browse/CMK-13531)
    items = ["_2host", "Host3", "Host1", "host2", "_1host", "2host", "123host", "124Host"]
    correct_order = ["2host", "123host", "124Host", "Host1", "host2", "Host3", "_1host", "_2host"]

    sorted_items = natural_sort(items)

    assert sorted_items == correct_order
