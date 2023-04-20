#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Iterator

import pytest
from pytest_mock import MockerFixture

from tests.testlib.plugin_registry import reset_registries

from livestatus import SiteId

from cmk.gui.plugins.wato.check_mk_configuration import ConfigVariableGroupUserInterface
from cmk.gui.plugins.watolib.utils import config_variable_registry, ConfigVariable
from cmk.gui.valuespec import TextInput, Transform
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    load_site_global_settings,
    save_global_settings,
    save_site_global_settings,
)
from cmk.gui.watolib.sites import SiteManagementFactory

from cmk.update_config.plugins.actions import global_settings


@pytest.fixture(name="plugin")
def fixture_plugin() -> global_settings.UpdateGlobalSettings:
    return global_settings.UpdateGlobalSettings(
        name="global_settings",
        title="Global settings",
        sort_index=20,
    )


@pytest.fixture(name="test_var")
def fixture_test_var(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    test_var_name = "test_var"

    class ConfigVariableTestVar(ConfigVariable):
        def group(self):
            return ConfigVariableGroupUserInterface

        def domain(self):
            return ConfigDomainGUI

        def ident(self):
            return test_var_name

        def valuespec(self):
            return Transform(TextInput(), forth=lambda x: "new" if x == "old" else x)

    with reset_registries([config_variable_registry]):
        config_variable_registry.register(ConfigVariableTestVar)
        yield test_var_name


def test_update_global_config_transform_values(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    test_var: str,
) -> None:
    # Disable variable filtering by known Checkmk variables
    mocker.patch.object(
        global_settings, "filter_unknown_settings", lambda global_config: global_config
    )

    assert global_settings.update_global_config(logging.getLogger(), {test_var: "old"}) == {
        test_var: "new"
    }


def test_update_global_config_rename_variables_and_change_values(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        global_settings,
        "_REMOVED_GLOBALS",
        [
            ("global_a", "new_global_a", {True: 1, False: 0}),
            ("global_b", "new_global_b", {}),
            ("missing", "new_missing", {}),
        ],
    )

    # Disable variable filtering by known Checkmk variables
    mocker.patch.object(
        global_settings, "filter_unknown_settings", lambda global_config: global_config
    )

    assert global_settings.update_global_config(
        logging.getLogger(),
        {
            "global_a": True,
            "global_b": 14,
            "keep": "do not remove me",
            "unknown": "How did this get here?",
        },
    ) == {
        "keep": "do not remove me",
        "unknown": "How did this get here?",
        "new_global_a": 1,
        "new_global_b": 14,
    }


@pytest.mark.usefixtures("request_context")
def test_update_global_settings_migrates_global_settings(
    plugin: global_settings.UpdateGlobalSettings, test_var: str
) -> None:
    save_global_settings(
        {
            "test_var": "old",
        }
    )
    plugin(logging.getLogger(), {})
    assert load_configuration_settings(full_config=True) == {"test_var": "new"}


@pytest.mark.usefixtures("request_context")
def test_update_global_settings_migrates_site_specific_settings(
    monkeypatch: pytest.MonkeyPatch, plugin: global_settings.UpdateGlobalSettings, test_var: str
) -> None:
    monkeypatch.setattr(global_settings, "is_wato_slave_site", lambda: True)
    save_site_global_settings(
        {
            "test_var": "old",
        }
    )
    plugin(logging.getLogger(), {})
    assert load_site_global_settings() == {"test_var": "new"}


@pytest.mark.usefixtures("request_context")
def test_update_global_settings_migrates_remote_site_specific_settings(
    monkeypatch: pytest.MonkeyPatch, plugin: global_settings.UpdateGlobalSettings, test_var: str
) -> None:
    monkeypatch.setattr(global_settings, "site_globals_editable", lambda site, spec: True)
    site_mgmt = SiteManagementFactory().factory()
    configured_sites = site_mgmt.load_sites()
    configured_sites[SiteId("NO_SITE")]["globals"] = {"test_var": "old"}
    site_mgmt.save_sites(configured_sites, activate=False)

    plugin(logging.getLogger(), {})
    assert site_mgmt.load_sites()[SiteId("NO_SITE")]["globals"] == {"test_var": "new"}
