#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools

import pytest

from cmk.gui.search.sorting import get_sorter
from cmk.gui.search.type_defs import UnifiedSearchResultItem

I = functools.partial(UnifiedSearchResultItem, url="", provider="setup")


def get_results_alphabetically() -> list[UnifiedSearchResultItem]:
    return [
        I(title="Certificate overview", topic="Setup"),
        I(title="Cisco Meraki Organisation Licenses Overview", topic="Enforced services"),
        I(title="Cisco Meraki Organisation Licenses Overview", topic="Service monitoring rules"),
        I(title="Couchbase Node: Size of couch views", topic="Enforced services"),
        I(title="Couchbase Node: Size of couch views", topic="Service monitoring rules"),
        I(title="Couchbase Node: Size of spacial views", topic="Enforced services"),
        I(title="Couchbase Node: Size of spacial views", topic="Service monitoring rules"),
        I(title="Hide hosttags in Setup folder view", topic="Global settings"),
        I(title="Limit the number of rows in View tables", topic="Global settings"),
        I(title="Sounds in Views", topic="Global settings"),
        I(title="Threshold for slow views", topic="Global settings"),
        I(title="Views", topic="Visualization", provider="customize"),
    ]


@pytest.mark.xfail(reason="CMK-25121: improve weighted sorting")
def test_weighted_index_sorting_with_view_query() -> None:
    results = get_results_alphabetically()
    get_sorter("weighted_index", query="view")(results)

    value = [(result.title, result.topic) for result in results]
    expected = [
        ("Views", "Visualization"),  # customize
        ("Couchbase Node: Size of couch views", "Service monitoring rules"),
        ("Couchbase Node: Size of spacial views", "Service monitoring rules"),
        ("Hide hosttags in Setup folder view", "Global settings"),
        ("Limit the number of rows in View tables", "Global settings"),
        ("Sounds in Views", "Global settings"),
        ("Threshold for slow views", "Global settings"),
        ("Couchbase Node: Size of couch views", "Enforced services"),
        ("Couchbase Node: Size of spacial views", "Enforced services"),
        ("Certificate overview", "Setup"),
        ("Cisco Meraki Organisation Licenses Overview", "Service monitoring rules"),
        ("Cisco Meraki Organisation Licenses Overview", "Enforced services"),
    ]

    assert value == expected
