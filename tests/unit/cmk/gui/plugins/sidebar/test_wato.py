#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List

import pytest

import cmk.utils.version as cmk_version

from cmk.gui.plugins.sidebar.wato import get_wato_menu_items, MatchItemGeneratorSetupMenu
from cmk.gui.type_defs import TopicMenuItem, TopicMenuTopic
from cmk.gui.watolib.search import MatchItem


def expected_items() -> Dict[str, List[str]]:
    agents_items = []

    if cmk_version.is_raw_edition():
        agents_items += [
            "download_agents_linux",
            "download_agents_windows",
        ]
    else:
        agents_items += [
            "agents",
        ]

    agents_items += [
        "download_agents",
    ]

    if not cmk_version.is_raw_edition():
        agents_items.append("agent_registration")

    agents_items += [
        "wato.py?group=vm_cloud_container&mode=rulesets",
        "wato.py?group=datasource_programs&mode=rulesets",
        "wato.py?group=agent&mode=rulesets",
        "wato.py?group=snmp&mode=rulesets",
    ]

    events_items = [
        "notifications",
        "mkeventd_rule_packs",
    ]

    if not cmk_version.is_raw_edition():
        events_items.append("alert_handlers")

    maintenance_items = ["backup"]

    if not cmk_version.is_raw_edition():
        maintenance_items.append("license_usage")
        maintenance_items.append("mkps")

    maintenance_items += [
        "diagnostics",
        "analyze_config",
        "background_jobs_overview",
    ]

    hosts_items = [
        "folder",
        "wato.py?group=host_monconf&mode=rulesets",
        "tags",
    ]

    if not cmk_version.is_raw_edition():
        hosts_items.append("dcd_connections")

    hosts_items += [
        "host_groups",
        "host_attrs",
        "wato.py?group=inventory&mode=rulesets",
    ]

    users_items = [
        "users",
        "contact_groups",
        "roles",
        "ldap_config",
        "user_attrs",
    ]

    if cmk_version.is_managed_edition():
        users_items.insert(0, "customer_management")

    expected_items_dict = {
        "agents": agents_items,
        "events": events_items,
        "general": [
            "rule_search",
            "globalvars",
            "read_only",
            "predefined_conditions",
            "timeperiods",
            "passwords",
            "sites",
            "auditlog",
            "icons",
        ],
        "hosts": hosts_items,
        "maintenance": maintenance_items,
        "services": [
            "wato.py?group=monconf&mode=rulesets",
            "wato.py?group=checkparams&mode=rulesets",
            "wato.py?group=static&mode=rulesets",
            "wato.py?group=activechecks&mode=rulesets",
            "wato.py?group=custom_checks&mode=rulesets",
            "service_groups",
            "check_plugins",
        ],
        "bi": ["bi_packs"],
        "users": users_items,
    }

    if not cmk_version.is_raw_edition():
        expected_items_dict.update({"exporter": ["influxdb_connections"]})

    return expected_items_dict


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_get_wato_menu_items():
    items_by_topic: Dict[str, List[str]] = {}
    for topic in get_wato_menu_items():
        items = items_by_topic.setdefault(topic.name, [])
        for item in topic.items:
            items.append(item.name)

    assert expected_items() == items_by_topic


@pytest.mark.usefixtures("with_admin_login")
def test_unique_wato_menu_item_titels():
    titles = [
        entry.title
        for topic_menu_topic in get_wato_menu_items()
        for entry in topic_menu_topic.items
    ]
    assert len(titles) == len(set(titles))


def test_match_item_generator_setup_menu():
    assert list(
        MatchItemGeneratorSetupMenu(
            "setup",
            lambda: [
                TopicMenuTopic(
                    name="topic",
                    title="Topic",
                    items=[
                        TopicMenuItem(name="item 1", title="Item 1", sort_index=0, url="url 1"),
                        TopicMenuItem(name="item 2", title="Item 2", sort_index=1, url="url 2"),
                    ],
                )
            ],
        ).generate_match_items()
    ) == [
        MatchItem(title="Item 1", topic="Setup", url="url 1", match_texts=["item 1"]),
        MatchItem(title="Item 2", topic="Setup", url="url 2", match_texts=["item 2"]),
    ]
