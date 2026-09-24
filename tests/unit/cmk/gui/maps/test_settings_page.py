#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.i18n import _l
from cmk.gui.watolib.config_domain_name import ConfigVariableGroup
from cmk.maps.gui._config_domain import (
    CONFIG_VAR_CONNECTIONS,
    CONFIG_VAR_LOG_LEVEL,
    CONFIG_VAR_MAP_DEFAULTS,
    CONFIG_VAR_OBJECT_DEFAULTS,
    CONFIG_VAR_STATE_REFRESH_INTERVAL,
    ConfigDomainMaps,
)
from cmk.maps.gui._settings_page import maps_settings
from cmk.shared_typing.global_settings import GlobalSettingsOrigin
from tests.testlib.unit.gui.global_settings import (
    logged_in,
    patch_factory_defaults,
    registered,
    shown_variables,
)

GUI_VAR = "test_gui_var"


@pytest.fixture(name="maps_and_gui_variables")
def fixture_maps_and_gui_variables(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    patch_factory_defaults(monkeypatch, {**ConfigDomainMaps().default_globals(), GUI_VAR: 1})
    with registered(ConfigVariableGroup(title=_l("GUI group"), sort_index=1), GUI_VAR):
        yield


@pytest.mark.usefixtures("maps_and_gui_variables", "with_admin_login")
def test_the_page_shows_the_maps_variables_in_their_two_topics(load_config: Config) -> None:
    data = maps_settings(load_config)

    assert {
        topic.headline: {variable.name for variable in topic.variables} for topic in data.topics
    } == {
        "Maps: Map and object defaults": {CONFIG_VAR_MAP_DEFAULTS, CONFIG_VAR_OBJECT_DEFAULTS},
        "Maps: Connections & daemon": {
            CONFIG_VAR_CONNECTIONS,
            CONFIG_VAR_LOG_LEVEL,
            CONFIG_VAR_STATE_REFRESH_INTERVAL,
        },
    }


@pytest.mark.usefixtures("maps_and_gui_variables", "with_admin_login")
def test_a_fresh_site_lists_its_own_connection_unmodified(load_config: Config) -> None:
    connections = shown_variables(maps_settings(load_config))[CONFIG_VAR_CONNECTIONS]

    assert connections.origin is GlobalSettingsOrigin.factory
    assert connections.value


@pytest.mark.usefixtures("maps_and_gui_variables")
def test_the_maps_configure_permission_suffices_for_the_page(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with logged_in(with_user[0], "wato.use", "maps.configure"):
        assert shown_variables(maps_settings(load_config))


def test_the_page_refuses_a_user_with_only_the_global_settings_permission(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with (
        logged_in(with_user[0], "wato.use", "wato.global"),
        pytest.raises(MKAuthException),
    ):
        maps_settings(load_config)


@pytest.mark.usefixtures("maps_and_gui_variables", "with_admin_login")
def test_the_breadcrumb_hangs_under_the_map_list(load_config: Config) -> None:
    data = maps_settings(load_config)

    assert [item.title for item in data.breadcrumb] == ["Customize", "Maps", "Maps settings"]
    assert data.breadcrumb[1].link == "maps.py"
