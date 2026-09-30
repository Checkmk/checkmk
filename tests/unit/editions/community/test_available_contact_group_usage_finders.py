#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.groups_io import contact_group_usage_finder_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_group_usage_finder_registry_entries() -> None:
    expected = [
        "find_usages_of_contact_group_in_dashboards",
        "find_usages_of_contact_group_in_default_user_profile",
        "find_usages_of_contact_group_in_ec_rules",
        "find_usages_of_contact_group_in_hosts_and_folders",
        "find_usages_of_contact_group_in_mkeventd_notify_contactgroup",
        "find_usages_of_contact_group_in_notification_rules",
        "find_usages_of_contact_group_in_users",
    ]

    registered = [f.__name__ for f in contact_group_usage_finder_registry.values()]
    assert sorted(registered) == sorted(expected)
