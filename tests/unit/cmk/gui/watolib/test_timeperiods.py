#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.watolib.timeperiods import timeperiod_usage_finder_registry
from tests.testlib.common.repo import is_enterprise_repo


def test_group_usage_finder_registry_entries() -> None:
    expected = [
        "find_timeperiod_usage_in_ec_rules",
        "find_timeperiod_usage_in_host_and_service_rules",
        "find_timeperiod_usage_in_notification_rules",
        "find_timeperiod_usage_in_time_specific_parameters",
        "find_timeperiod_usage_in_users",
    ]

    if is_enterprise_repo():
        expected.append("find_timeperiod_usage_in_alert_handler_rules")

    registered = [f.__name__ for f in timeperiod_usage_finder_registry.values()]
    assert sorted(registered) == sorted(expected)
