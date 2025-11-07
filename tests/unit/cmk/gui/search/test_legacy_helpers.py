#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.search.legacy_helpers import transform_legacy_results_to_unified
from cmk.gui.type_defs import SearchResult
from cmk.gui.utils.loading_transition import LoadingTransition


def test_transform_legacy_results_to_unified() -> None:
    topic = "common"
    results = [
        SearchResult(context="", title="Hosts", url="/hosts"),
        SearchResult(context="", title="Notifications", url="/notifications"),
        SearchResult(context="", title="User", url="/users"),
        SearchResult(context="", title="Foo", url="/foo", loading_transition="table"),
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
            "target": {
                "url": "/hosts",
                "transition": None,
            },
            "icon": "main-setup-active",
        },
        {
            "context": "",
            "provider": "setup",
            "title": "Notifications",
            "topic": "common",
            "target": {
                "url": "/notifications",
                "transition": None,
            },
            "icon": "main-setup-active",
        },
        {
            "context": "",
            "provider": "setup",
            "title": "User",
            "topic": "common",
            "target": {
                "url": "/users",
                "transition": None,
            },
            "icon": "main-setup-active",
        },
        {
            "context": "",
            "provider": "setup",
            "title": "Foo",
            "topic": "common",
            "target": {
                "url": "/foo",
                "transition": LoadingTransition.table,
            },
            "icon": "main-setup-active",
        },
    ]

    assert value == expected
