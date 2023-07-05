#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from cmk.utils.hostaddress import HostName
from cmk.utils.user import UserId

from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.update_config.plugins.actions.hosts_and_folders import UpdateHostsAndFolders


def run_plugin() -> None:
    return UpdateHostsAndFolders(
        name="hosts_and_folders",
        title="Hosts and folders",
        sort_index=40,
    )(logging.getLogger(), {})


def test_update_tuple_contact_groups_in_folder() -> None:
    folder = folder_tree().root_folder()
    folder.attributes["contactgroups"] = (False, [])

    run_plugin()

    assert folder.attributes["contactgroups"] == {
        "groups": [],
        "recurse_perms": False,
        "recurse_use": False,
        "use": False,
        "use_for_services": False,
    }


def test_update_tuple_contact_groups_in_host(with_admin_login: UserId) -> None:
    folder = folder_tree().root_folder()
    hostname = HostName("testhost")
    folder.create_hosts([(hostname, {}, [])])
    host = folder.load_host(hostname)
    host.attributes["contactgroups"] = (True, ["a", "b"])

    run_plugin()

    assert folder.load_host(hostname).attributes["contactgroups"] == {
        "groups": ["a", "b"],
        "recurse_perms": False,
        "recurse_use": False,
        "use": True,
        "use_for_services": False,
    }
