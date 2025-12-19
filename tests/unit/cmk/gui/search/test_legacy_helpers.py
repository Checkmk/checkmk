#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.search.legacy_helpers import (
    transform_legacy_loading_transition_to_unified,
    transform_legacy_results_to_unified,
)
from cmk.gui.type_defs import SearchResult
from cmk.shared_typing.unified_search import LoadingTransition, ProviderName


def test_transform_legacy_results_to_unified() -> None:
    topic = "common"
    results = [
        SearchResult(context="", title="Hosts", url="/hosts"),
        SearchResult(context="", title="Notifications", url="/notifications"),
        SearchResult(context="", title="User", url="/users"),
        SearchResult(context="", title="Foo", url="/foo", loading_transition="table"),
    ]

    value = [
        asdict(result)
        for result in transform_legacy_results_to_unified(
            results, topic, provider=ProviderName.setup
        )
    ]
    expected = [
        {
            "context": "",
            "provider": ProviderName.setup,
            "title": "Hosts",
            "topic": "common",
            "target": {
                "url": "/hosts",
                "transition": None,
            },
            "inline_buttons": None,
            "icon": None,
        },
        {
            "context": "",
            "provider": ProviderName.setup,
            "title": "Notifications",
            "topic": "common",
            "target": {
                "url": "/notifications",
                "transition": None,
            },
            "inline_buttons": None,
            "icon": None,
        },
        {
            "context": "",
            "provider": ProviderName.setup,
            "title": "User",
            "topic": "common",
            "target": {
                "url": "/users",
                "transition": None,
            },
            "inline_buttons": None,
            "icon": None,
        },
        {
            "context": "",
            "provider": ProviderName.setup,
            "title": "Foo",
            "topic": "common",
            "target": {
                "url": "/foo",
                "transition": LoadingTransition.table,
            },
            "inline_buttons": None,
            "icon": None,
        },
    ]

    assert value == expected


def test_transform_legacy_loading_transition_to_unified() -> None:
    # Test None input returns None
    assert transform_legacy_loading_transition_to_unified(None) is None

    # Test valid transition strings return correct enum values
    assert transform_legacy_loading_transition_to_unified("table") == LoadingTransition.table
    assert transform_legacy_loading_transition_to_unified("catalog") == LoadingTransition.catalog
    assert (
        transform_legacy_loading_transition_to_unified("dashboard") == LoadingTransition.dashboard
    )

    # Test invalid transition string returns None
    assert transform_legacy_loading_transition_to_unified("invalid_transition") is None
    assert transform_legacy_loading_transition_to_unified("") is None
    assert transform_legacy_loading_transition_to_unified("unknown") is None
