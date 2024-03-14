#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils.sort import natural_sort


def test_natural_sort() -> None:
    # Test if natural sort function complies with criteria requested (https://jira.lan.tribe29.com/browse/CMK-13531)
    items = ["_2host", "Host3", "Host1", "host2", "_1host", "2host", "123host", "124Host"]
    correct_order = ["_1host", "_2host", "2host", "123host", "124Host", "Host1", "host2", "Host3"]

    sorted_items = natural_sort(items)

    assert sorted_items == correct_order


def test_natural_sort_dict() -> None:
    items = {
        "key1": "_2host",
        "key2": "Host3",
        "key3": "Host1",
        "key4": "host2",
        "key5": "_1host",
        "key6": "2host",
        "key7": "123host",
        "key8": "124Host",
        "key9": "host2",
    }
    correct_order = ["key5", "key1", "key6", "key7", "key8", "key3", "key4", "key9", "key2"]

    sorted_items = natural_sort(items)

    assert sorted_items == correct_order
