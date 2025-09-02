#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools

from cmk.gui.search.sorting import get_sorter
from cmk.gui.search.type_defs import UnifiedSearchResultItem

I = functools.partial(UnifiedSearchResultItem, url="", provider="setup")


def get_results_alphabetically() -> list[UnifiedSearchResultItem]:
    return [
        I(title="Analyze recent notifications", topic="Setup"),
        I(title="Delay host notifications", topic="Host monitoring rules"),
        I(title="Delay service notifications", topic="Service monitoring rules"),
        I(title="Enable/disable notifications for hosts", topic="Host monitoring rules"),
        I(title="Enable/disable notifications for services", topic="Service monitoring rules"),
        I(title="Failed notifications", topic="Monitor", provider="monitoring"),
        I(title="Fallback email address for notifications", topic="Global settings"),
        I(title="Interval for checking for ripe bulk notifications", topic="Global settings"),
        I(title="Logging of the notification mechanics", topic="Global settings"),
        I(title="Notifications of host & services", topic="Monitor", provider="monitoring"),
        I(title="Notifications", topic="Setup"),
        I(title="Periodic notifications during host problems", topic="Host monitoring rules"),
        I(title="Periodic notifications during service problems", topic="Service monitoring rules"),
        I(title="Push Notifications (using Pushover)", topic="Notification parameter"),
        I(title="Push Notifications (using Pushover)", topic="Service monitoring rules"),
        I(title="Send notifications to Event Console", topic="Global settings"),
        I(title="Send notifications to remote Event Console", topic="Global settings"),
        I(title="Store notifications for rule analysis", topic="Global settings"),
        I(title="Syslog facility for Event console notifications", topic="Global settings"),
        I(title="Test notifications", topic="Setup"),
    ]


def test_weighted_index_sorting_with_notifications_query() -> None:
    results = get_results_alphabetically()
    get_sorter("weighted_index", query="notifications")(results)

    value = [(result.title, result.topic) for result in results]
    expected = [
        ("Notifications", "Setup"),
        ("Notifications of host & services", "Monitor"),
        ("Analyze recent notifications", "Setup"),
        ("Test notifications", "Setup"),
        ("Failed notifications", "Monitor"),
        ("Delay host notifications", "Host monitoring rules"),
        ("Enable/disable notifications for hosts", "Host monitoring rules"),
        ("Periodic notifications during host problems", "Host monitoring rules"),
        ("Push Notifications (using Pushover)", "Notification parameter"),
        ("Delay service notifications", "Service monitoring rules"),
        ("Enable/disable notifications for services", "Service monitoring rules"),
        ("Periodic notifications during service problems", "Service monitoring rules"),
        ("Fallback email address for notifications", "Global settings"),
        ("Interval for checking for ripe bulk notifications", "Global settings"),
        ("Logging of the notification mechanics", "Global settings"),
        ("Send notifications to Event Console", "Global settings"),
        ("Send notifications to remote Event Console", "Global settings"),
        ("Store notifications for rule analysis", "Global settings"),
        ("Syslog facility for Event console notifications", "Global settings"),
        ("Push Notifications (using Pushover)", "Service monitoring rules"),
    ]

    assert value == expected
