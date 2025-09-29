#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.search.legacy_helpers import transform_legacy_results_to_unified
from cmk.gui.type_defs import SearchResult


def test_transform_legacy_results_to_unified() -> None:
    topic = "common"
    results = [
        SearchResult(context="", title="Hosts", url="/hosts"),
        SearchResult(context="", title="Notifications", url="/notifications"),
        SearchResult(context="", title="User", url="/users"),
    ]

    value = [
        result.serialize()
        for result in transform_legacy_results_to_unified(results, topic, provider="setup")
    ]
    expected = [
        {
            "context": "",
            "provider": "setup",
            "title": "Hosts",
            "topic": "common",
            "url": "/hosts",
        },
        {
            "context": "",
            "provider": "setup",
            "title": "Notifications",
            "topic": "common",
            "url": "/notifications",
        },
        {
            "context": "",
            "provider": "setup",
            "title": "User",
            "topic": "common",
            "url": "/users",
        },
    ]

    assert value == expected
