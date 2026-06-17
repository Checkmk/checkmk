#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.search import MatchItem
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato._snapins import get_wato_menu_items, MatchItemGeneratorSetupMenu
from cmk.shared_typing.main_menu import NavItemTopic, NavItemTopicEntry


def expected_items() -> dict[str, list[str]]:
    return {
        "agents": [
            "download_agents_linux",
            "download_agents_windows",
            "download_agents",
            "wato.py?group=vm_cloud_container&mode=rulesets",
            "wato.py?group=datasource_programs&mode=rulesets",
            "wato.py?group=agent&mode=rulesets",
            "wato.py?group=snmp&mode=rulesets",
        ],
        "events": [
            "notifications",
            "analyze_notifications",
            "test_notifications",
            "mkeventd_rule_packs",
        ],
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
        "hosts": [
            "folder",
            "wato.py?group=host_monconf&mode=rulesets",
            "tags",
            "host_groups",
            "host_attrs",
            "wato.py?group=inventory&mode=rulesets",
        ],
        "maintenance": [
            "backup",
            "diagnostics",
            "certificate_overview",
            "analyze_config",
            "background_jobs_overview",
        ],
        "quick_setups": [
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aaws",
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aazure",
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Agcp",
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aazure_v2",
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aproxmox_ve",
        ],
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
        "users": [
            "users",
            "contact_groups",
            "roles",
            "ldap_config",
            "user_attrs",
        ],
        "exporter": ["microsoft_entra_id_connections"],
    }


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_get_wato_menu_items() -> None:
    items_by_topic: dict[str, list[str]] = {}
    for topic in get_wato_menu_items(UserPermissions({}, {}, {}, [])):
        items = items_by_topic.setdefault(topic.id, [])
        for item in topic.entries:
            items.append(item.id)

    assert expected_items() == items_by_topic


@pytest.mark.usefixtures("with_admin_login")
def test_unique_wato_menu_item_titels() -> None:
    titles = [
        entry.title
        for main_menu_topic in get_wato_menu_items(UserPermissions({}, {}, {}, []))
        for entry in main_menu_topic.entries
    ]
    assert len(titles) == len(set(titles))


def test_match_item_generator_setup_menu() -> None:
    assert list(
        MatchItemGeneratorSetupMenu(
            "setup",
            lambda p: [
                NavItemTopic(
                    id="topic",
                    title="Topic",
                    entries=[
                        NavItemTopicEntry(id="item 1", title="Item 1", sort_index=0, url="url 1"),
                        NavItemTopicEntry(id="item 2", title="Item 2", sort_index=1, url="url 2"),
                    ],
                    sort_index=0,
                )
            ],
        ).generate_match_items(UserPermissions({}, {}, {}, []))
    ) == [
        MatchItem(title="Item 1", topic="Setup", url="url 1", match_texts=["item 1"]),
        MatchItem(title="Item 2", topic="Setup", url="url 2", match_texts=["item 2"]),
    ]
