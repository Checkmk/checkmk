#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.ccc.version as cmk_version
from cmk.gui.main_menu_types import MainMenuItem, MainMenuTopic
from cmk.gui.search import MatchItem
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato._snapins import get_wato_menu_items, MatchItemGeneratorSetupMenu
from cmk.utils import paths


def expected_items() -> dict[str, list[str]]:
    agents_items = []

    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.COMMUNITY:
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

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        agents_items.append("agent_registration")

    agents_items += [
        "wato.py?group=vm_cloud_container&mode=rulesets",
        "wato.py?group=datasource_programs&mode=rulesets",
        "wato.py?group=agent&mode=rulesets",
        "wato.py?group=snmp&mode=rulesets",
    ]

    events_items = [
        "notifications",
        "analyze_notifications",
        "test_notifications",
        "mkeventd_rule_packs",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        events_items.append("alert_handlers")

    maintenance_items = ["backup"]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        maintenance_items.append("licensing")
        maintenance_items.append("mkps")

    maintenance_items += [
        "diagnostics",
        "certificate_overview",
        "analyze_config",
        "background_jobs_overview",
    ]

    hosts_items = [
        "folder",
        "wato.py?group=host_monconf&mode=rulesets",
        "tags",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        hosts_items.append("dcd_connections")

    hosts_items += [
        "host_groups",
        "host_attrs",
        "wato.py?group=inventory&mode=rulesets",
    ]

    if cmk_version.edition(paths.omd_root) in [
        cmk_version.Edition.ULTIMATE,
        cmk_version.Edition.ULTIMATEMT,
    ]:
        hosts_items.append("otel_collectors_receivers")
        hosts_items.append("otel_collectors_prom_scrapes")
        hosts_items.append("relays")

    users_items = []
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.ULTIMATEMT:
        users_items.append("customer_management")
    users_items.extend(
        [
            "users",
            "contact_groups",
            "roles",
            "ldap_config",
        ]
    )
    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        users_items.append("saml_config")
    users_items.append("user_attrs")

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
            "oauth2_connections",
            "sites",
            "auditlog",
            "icons",
        ],
        "hosts": hosts_items,
        "maintenance": maintenance_items,
        "quick_setups": [
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aaws",
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aazure",
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Agcp",
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aazure_v2",
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
        "users": users_items,
        "exporter": ["wato.py?connector_type=microsoft_entra_id&mode=oauth2_connections"],
    }

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        expected_items_dict.update(
            {
                "exporter": [
                    "influxdb_connections",
                    "wato.py?connector_type=microsoft_entra_id&mode=oauth2_connections",
                ],
                "synthetic_monitoring": ["robotmk_managed_robots_overview"],
            }
        )

    return expected_items_dict


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_get_wato_menu_items() -> None:
    items_by_topic: dict[str, list[str]] = {}
    for topic in get_wato_menu_items(UserPermissions({}, {}, {}, [])):
        items = items_by_topic.setdefault(topic.name, [])
        for item in topic.entries:
            items.append(item.name)

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
                MainMenuTopic(
                    name="topic",
                    title="Topic",
                    entries=[
                        MainMenuItem(name="item 1", title="Item 1", sort_index=0, url="url 1"),
                        MainMenuItem(name="item 2", title="Item 2", sort_index=1, url="url 2"),
                    ],
                )
            ],
        ).generate_match_items(UserPermissions({}, {}, {}, []))
    ) == [
        MatchItem(title="Item 1", topic="Setup", url="url 1", match_texts=["item 1"]),
        MatchItem(title="Item 2", topic="Setup", url="url 2", match_texts=["item 2"]),
    ]
