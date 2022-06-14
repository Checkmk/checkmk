#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# force loading of web API plugins
import cmk.utils.version as cmk_version

import cmk.gui.webapi  # noqa: F401 # pylint: disable=unused-import
from cmk.gui.plugins.webapi.utils import api_call_collection_registry
from cmk.gui.plugins.webapi.webapi import _format_missing_tags


def test_format_tags() -> None:
    output = _format_missing_tags({("hallo", "welt"), ("hello", "world"), ("hello", None)})
    assert output == "hallo:welt, hello:None, hello:world"


def test_registered_api_call_collections() -> None:
    registered_api_actions = (
        action  #
        for cls in api_call_collection_registry.values()  #
        for action in cls().get_api_calls().keys()
    )

    expected_api_actions = [
        "activate_changes",
        "execute_remote_automation",
        "add_contactgroup",
        "add_folder",
        "add_host",
        "add_hostgroup",
        "add_hosts",
        "add_servicegroup",
        "add_users",
        "bulk_discovery_start",
        "bulk_discovery_status",
        "delete_contactgroup",
        "delete_folder",
        "delete_host",
        "delete_hostgroup",
        "delete_hosts",
        "delete_servicegroup",
        "delete_site",
        "delete_users",
        "discover_services",
        "edit_contactgroup",
        "edit_folder",
        "edit_host",
        "edit_hostgroup",
        "edit_hosts",
        "edit_servicegroup",
        "edit_users",
        "get_all_contactgroups",
        "get_all_folders",
        "get_all_hostgroups",
        "get_all_hosts",
        "get_all_servicegroups",
        "get_all_sites",
        "get_all_users",
        "get_bi_aggregations",
        "get_combined_graph_identifications",
        "get_folder",
        "get_graph",
        "get_graph_annotations",
        "get_graph_recipes",
        "get_host",
        "get_host_names",
        "get_hosttags",
        "get_inventory",
        "get_metrics_of_host",
        "get_ruleset",
        "get_rulesets_info",
        "get_site",
        "get_user_sites",
        "login_site",
        "logout_site",
        "set_all_sites",
        "set_hosttags",
        "set_ruleset",
        "set_site",
    ]

    if not cmk_version.is_raw_edition():
        expected_api_actions += [
            "bake_agents",
            "get_sla",
        ]

    assert sorted(registered_api_actions) == sorted(expected_api_actions)
