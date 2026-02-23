#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from polyfactory.factories import DataclassFactory

from cmk.gui.search.collapsing import get_collapser
from cmk.shared_typing.unified_search import (
    ProviderName,
    UnifiedSearchResultCounts,
    UnifiedSearchResultItem,
)


class UnifiedSearchResultItemFactory(DataclassFactory[UnifiedSearchResultItem]):
    __check_model__ = False


def test_host_collapsing() -> None:
    initial_results = [
        UnifiedSearchResultItemFactory.build(
            title="testhost",
            provider=ProviderName.setup,
            topic="Hosts",
            target={"url": "/setup/testhost"},
        ),
        UnifiedSearchResultItemFactory.build(
            title="testhost",
            provider=ProviderName.monitoring,
            topic="Host name",
            target={"url": "/monitoring/testhost"},
        ),
        # Host alias does not get collapsed
        UnifiedSearchResultItemFactory.build(
            title="testhost",
            provider=ProviderName.monitoring,
            topic="Hostalias",
            target={"url": "/monitoring/testhost"},
        ),
    ]
    initial_count = UnifiedSearchResultCounts(total=3, setup=1, monitoring=2, customize=0)
    collapse = get_collapser(provider=None, disabled=False)

    results, counts = collapse(initial_results, initial_count)

    # expecting only one result here
    assert len(results) == 2

    # check that matching monitoring results were merged
    assert results[0].title == "testhost"
    assert results[0].provider == ProviderName.monitoring
    assert results[0].target.url == "/monitoring/testhost"

    # check the inline setup edit button
    assert results[0].inline_buttons
    assert results[0].inline_buttons[0].title == "Edit"
    assert results[0].inline_buttons[0].target.url == "/setup/testhost"

    # Host alias is second result
    assert results[1].topic == "Hostalias"

    # check that counts were updated accordingly
    assert counts == UnifiedSearchResultCounts(total=2, setup=1, monitoring=2, customize=0)


def test_host_collapsing_disabled() -> None:
    initial_results = [
        UnifiedSearchResultItemFactory.build(title="testhost", topic="Hosts"),
        UnifiedSearchResultItemFactory.build(title="testhost", topic="Host name"),
        UnifiedSearchResultItemFactory.build(title="Test Host", topic="Hostalias"),
    ]
    initial_counts = UnifiedSearchResultCounts(total=3, setup=1, monitoring=2, customize=0)
    collapse = get_collapser(provider=None, disabled=True)

    results, counts = collapse(initial_results, initial_counts)

    assert results == initial_results
    assert counts == initial_counts


def test_host_collapsing_ignored_with_only_setup_item() -> None:
    initial_results = [
        UnifiedSearchResultItemFactory.build(title="testhost", topic="Hosts"),
    ]
    initial_count = UnifiedSearchResultCounts(total=1, setup=1, monitoring=0, customize=0)
    collapse = get_collapser(provider=None, disabled=False)

    results, counts = collapse(initial_results, initial_count)

    # check that no transformation occurs when no monitoring items are available
    assert results == initial_results
    assert counts == initial_count


def test_host_name_topic_converted_to_hosts_without_setup_item() -> None:
    initial_results = [
        UnifiedSearchResultItemFactory.build(title="testhost", topic="Host name"),
    ]
    initial_count = UnifiedSearchResultCounts(total=1, setup=0, monitoring=1, customize=0)
    collapse = get_collapser(provider=None, disabled=False)

    results, counts = collapse(initial_results, initial_count)

    # We want the topic name to be consistent even if you cannot edit the host.
    assert results[0].topic == "Hosts"
