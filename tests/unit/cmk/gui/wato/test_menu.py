#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import Config
from cmk.gui.main_menu_match_items import MatchItemGeneratorMainMenu
from cmk.gui.permissions import permission_registry
from cmk.gui.search.matchers import MatchItem, MatchItemConfig
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato._snapins import get_wato_menu_items, SidebarSnapinWATOMini
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
            "global_settings.py",
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
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Akube_v2",
            "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aaws_v2",
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


@pytest.fixture(name="user_without_setup")
def fixture_user_without_setup(
    load_config: Config, with_user: tuple[UserId, str]
) -> Iterator[UserPermissions]:
    roles = copy.deepcopy(load_config.roles)
    roles["user"]["permissions"] = {**roles["user"].get("permissions", {}), "wato.use": False}
    user_id = UserId(with_user[0])
    permissions = UserPermissions(roles, permission_registry, {user_id: ["user"]}, [])
    with login.TransactionIdContext(user_id, permissions):
        yield permissions


@pytest.mark.usefixtures("request_context")
def test_setup_menu_is_empty_without_use_setup(user_without_setup: UserPermissions) -> None:
    assert get_wato_menu_items(user_without_setup) == []


@pytest.mark.usefixtures("request_context")
def test_setup_shortcuts_snapin_is_hidden_without_use_setup(
    user_without_setup: UserPermissions,
) -> None:
    assert not SidebarSnapinWATOMini.may_see(user_without_setup)


def test_match_item_generator_setup_menu() -> None:
    assert list(
        MatchItemGeneratorMainMenu(
            "setup",
            provider="setup",
            topic_generator=lambda p: [  # noqa: ARG005
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
            topic="Setup",
        ).generate_match_items(
            UserPermissions({}, {}, {}, []), MatchItemConfig.from_config(Config())
        )
    ) == [
        MatchItem(title="Item 1", topic="Setup", url="url 1", match_texts=["item 1"]),
        MatchItem(title="Item 2", topic="Setup", url="url 2", match_texts=["item 2"]),
    ]
