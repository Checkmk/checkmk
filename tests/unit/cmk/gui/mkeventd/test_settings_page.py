#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.i18n import _l
from cmk.gui.mkeventd._settings_page import event_console_settings, register
from cmk.gui.mkeventd.config_domain import ConfigDomainEventConsole
from cmk.gui.pages import PageRegistry
from cmk.gui.search.matchers import MatchItemGeneratorRegistry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.config_domain_name import ConfigVariableGroup
from tests.testlib.gui.global_settings import (
    logged_in,
    patch_factory_defaults,
    registered,
    shown_variables,
)

EVENT_CONSOLE_VAR = "test_ec_var"
GUI_VAR = "test_gui_var"


@pytest.fixture(name="variables_of_both_domains")
def fixture_variables_of_both_domains(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    patch_factory_defaults(monkeypatch, {EVENT_CONSOLE_VAR: 1, GUI_VAR: 2})
    with (
        registered(
            ConfigVariableGroup(title=_l("Event Console group"), sort_index=1),
            EVENT_CONSOLE_VAR,
            primary_domain=ConfigDomainEventConsole,
        ),
        registered(ConfigVariableGroup(title=_l("GUI group"), sort_index=2), GUI_VAR),
    ):
        yield


@pytest.mark.usefixtures("variables_of_both_domains", "with_admin_login")
def test_the_page_lists_only_event_console_variables(load_config: Config) -> None:
    assert set(shown_variables(event_console_settings(load_config))) == {EVENT_CONSOLE_VAR}


@pytest.mark.usefixtures("variables_of_both_domains", "load_config")
def test_the_search_index_lists_only_event_console_variables() -> None:
    match_item_generator_registry = MatchItemGeneratorRegistry()
    register(PageRegistry(), match_item_generator_registry)

    match_items = match_item_generator_registry["event_console_settings"].generate_match_items(
        UserPermissions({}, {}, {}, [])
    )

    assert [match_item.url for match_item in match_items] == [
        f"event_console_settings.py?varname={EVENT_CONSOLE_VAR}"
    ]


@pytest.mark.usefixtures("with_admin_login")
def test_a_disabled_event_console_refuses_the_page(load_config: Config) -> None:
    with pytest.raises(MKUserError, match="Event Console is disabled"):
        event_console_settings(dataclasses.replace(load_config, mkeventd_enabled=False))


@pytest.mark.usefixtures("variables_of_both_domains")
def test_the_event_console_permission_suffices_for_the_page(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with logged_in(with_user[0], "wato.use", "mkeventd.config"):
        event_console_settings(load_config)


def test_the_page_refuses_a_user_with_only_the_global_settings_permission(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with (
        logged_in(with_user[0], "wato.use", "wato.global"),
        pytest.raises(MKAuthException, match="Configuration of Event Console"),
    ):
        event_console_settings(load_config)


@pytest.mark.usefixtures("variables_of_both_domains", "with_admin_login")
def test_the_breadcrumb_hangs_under_the_event_console_rule_packs(load_config: Config) -> None:
    data = event_console_settings(load_config)

    assert [item.title for item in data.breadcrumb][-3:] == [
        "Events",
        "Event Console rule packs",
        "Event Console configuration",
    ]
    assert [item.link for item in data.breadcrumb][-2] == "wato.py?mode=mkeventd_rule_packs"
