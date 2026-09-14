#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest
from pytest_mock import MockerFixture

from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.config import active_config
from cmk.gui.plugins.wato.utils import ConfigVariableGroupUserInterface
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.wato._check_mk_configuration import ConfigVariableLogLevels
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.rulesets.v1.form_specs import String
from cmk.update_config.plugins.actions import global_settings
from tests.unit.cmk.update_config.plugins.actions.previous_release_fixtures import (
    previous_release_settings,
    UPDATED_PREVIOUS_RELEASE_SETTINGS,
)
from tests.unit.cmk.update_config.plugins.actions.site_mgmt_fakes import FakeSiteMgmt


@pytest.mark.usefixtures("request_context")
def test_update_global_config_migrates_form_spec_values(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Disable variable filtering by known Checkmk variables
    mocker.patch.object(
        global_settings, "filter_unknown_settings", lambda global_config: global_config
    )

    ConfigVariableKey = ConfigVariable(
        group=ConfigVariableGroupUserInterface,
        primary_domain=ConfigDomainGUI,
        ident="key",
        form_spec=lambda context: String(migrate=lambda x: "new" if x == "old" else str(x)),  # noqa: ARG005
    )

    registry = ConfigVariableRegistry()
    registry.register(ConfigVariableKey)
    monkeypatch.setattr(global_settings, "config_variable_registry", registry)

    assert global_settings.update_global_config(
        logging.getLogger(),
        {"key": "old"},
        active_config,
    ) == {"key": "new"}


@pytest.mark.usefixtures("request_context")
def test_update_global_config_migrates_renamed_log_level(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # CMK-36979: the automations logger was renamed cmk.web.automations ->
    # cmk.automations. A saved log_levels override must be rewritten during
    # cmk-update-config so the configured level is preserved under the new key.

    # Disable variable filtering by known Checkmk variables
    mocker.patch.object(
        global_settings, "filter_unknown_settings", lambda global_config: global_config
    )

    registry = ConfigVariableRegistry()
    registry.register(ConfigVariableLogLevels(Edition.COMMUNITY))
    monkeypatch.setattr(global_settings, "config_variable_registry", registry)

    assert global_settings.update_global_config(
        logging.getLogger(),
        {"log_levels": {"cmk.web": 30, "cmk.web.automations": 10}},
        active_config,
    ) == {
        "log_levels": {
            "cmk.web": 30,
            "cmk.automations": 10,
        }
    }


def test_update_global_config(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        global_settings,
        "_RENAMED_GLOBALS",
        [
            ("global_a", "new_global_a", {True: 1, False: 0}),
            ("global_b", "new_global_b", {}),
            ("missing", "new_missing", {}),
        ],
    )
    mocker.patch.object(
        global_settings,
        "_REMOVED_OPTIONS",
        ["old_unused"],
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
            "old_unused": "remove me",
            "unknown": "How did this get here?",
        },
        active_config,
    ) == {
        "keep": "do not remove me",
        "unknown": "How did this get here?",
        "new_global_a": 1,
        "new_global_b": 14,
    }


def test_remove_options() -> None:
    assert global_settings._remove_options(  # noqa: SLF001
        logging.getLogger(),
        {
            "global_a": True,
            "global_b": 14,
            "old_unused": "remove me",
            "unknown": "How did this get here?",
        },
        ["old_unused"],
    ) == {
        "global_a": True,
        "global_b": 14,
        "unknown": "How did this get here?",
    }


def test_update_global_config_normalizes_only_non_string_user_icons(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        global_settings, "filter_unknown_settings", lambda global_config: global_config
    )
    mocker.patch.object(
        global_settings, "_transform_global_config_values", lambda settings, _: settings
    )

    assert global_settings.update_global_config(
        logging.getLogger(),
        {
            "user_icons_and_actions": {
                # string icon values are left untouched (recoverable / runtime-handled)
                "valid": {"icon": "status", "title": "Valid"},
                "empty_string": {"icon": "", "title": "Empty string"},
                "non_dict": "broken",
                # non-string icon values are migrated to the missing icon
                "none_icon": {"icon": None, "title": "None icon"},
                "missing_key": {"title": "Missing key"},
                "bool_icon": {"icon": True, "title": "Bool icon"},
                "int_icon": {"icon": 123, "title": "Integer icon"},
            }
        },
        active_config,
    ) == {
        "user_icons_and_actions": {
            "valid": {"icon": "status", "title": "Valid"},
            "empty_string": {"icon": "", "title": "Empty string"},
            "non_dict": "broken",
            "none_icon": {"icon": "missing", "title": "None icon"},
            "missing_key": {"icon": "missing", "title": "Missing key"},
            "bool_icon": {"icon": "missing", "title": "Bool icon"},
            "int_icon": {"icon": "missing", "title": "Integer icon"},
        }
    }


def _register_migrating_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Register one setting that turns ``"old"`` into ``"new"``."""
    registry = ConfigVariableRegistry()
    registry.register(
        ConfigVariable(
            group=ConfigVariableGroupUserInterface,
            primary_domain=ConfigDomainGUI,
            ident="key",
            form_spec=lambda context: String(migrate=lambda x: "new" if x == "old" else str(x)),  # noqa: ARG005
        )
    )
    monkeypatch.setattr(global_settings, "config_variable_registry", registry)


@pytest.mark.usefixtures("request_context")
def test_update_global_config_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the update twice changes nothing the second time: not the
    migrated value, not the renamed setting, not the removed one."""
    monkeypatch.setattr(
        global_settings, "filter_unknown_settings", lambda global_config: global_config
    )
    monkeypatch.setattr(global_settings, "_RENAMED_GLOBALS", [("old_name", "new_name", {})])
    monkeypatch.setattr(global_settings, "_REMOVED_OPTIONS", ["withdrawn"])
    _register_migrating_key(monkeypatch)

    once = global_settings.update_global_config(
        logging.getLogger(),
        {"key": "old", "old_name": 14, "withdrawn": "drop me"},
        active_config,
    )
    twice = global_settings.update_global_config(logging.getLogger(), dict(once), active_config)

    assert once == {"key": "new", "new_name": 14}
    assert twice == once


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "is_remote_site",
    [
        pytest.param(True, id="remote"),
        pytest.param(
            False,
            id="central",
            marks=pytest.mark.xfail(
                strict=True,
                reason="the update skips a central site's sitespecific.mk",
            ),
        ),
    ],
)
def test_site_specific_settings_are_converted(
    monkeypatch: pytest.MonkeyPatch, is_remote_site: bool
) -> None:
    """Every site uses its own sitespecific.mk, so the update must convert it,
    on a remote and on a central site alike."""
    monkeypatch.setattr(
        global_settings, "is_distributed_setup_remote_site", lambda _sites: is_remote_site
    )
    monkeypatch.setattr(global_settings, "load_site_global_settings", previous_release_settings)
    saved: list[GlobalSettings] = []
    monkeypatch.setattr(global_settings, "save_site_global_settings_raw", saved.append)

    global_settings._update_site_specific_global_settings(logging.getLogger(), active_config)  # noqa: SLF001

    assert saved == [UPDATED_PREVIOUS_RELEASE_SETTINGS]


@pytest.mark.usefixtures("request_context")
def test_site_settings_in_the_central_config_are_converted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The central site keeps each site's own settings in sites.mk. The update
    converts them for the central and for remotes it replicates to, and
    leaves everything else in the entry alone. A remote without replication
    has no such settings, so its entry stays as it is."""
    fake = FakeSiteMgmt(
        {
            SiteId("central"): {
                "globals": previous_release_settings(),
                "socket": ("local", None),
            },
            SiteId("replicated"): {
                "globals": previous_release_settings(),
                "socket": ("tcp", {"address": ("replicated", 6557)}),
                "replication": "slave",
            },
            SiteId("unreplicated"): {
                "globals": previous_release_settings(),
                "socket": ("tcp", {"address": ("unreplicated", 6557)}),
                "replication": None,
            },
        }
    )
    monkeypatch.setattr(global_settings, "site_management_registry", {"site_management": fake})
    monkeypatch.setattr(global_settings, "make_folder_tree", lambda _config: None)

    global_settings._update_remote_site_specific_global_settings(logging.getLogger(), active_config)  # noqa: SLF001

    assert fake.saved == {
        SiteId("central"): {
            "globals": dict(UPDATED_PREVIOUS_RELEASE_SETTINGS),
            "socket": ("local", None),
        },
        SiteId("replicated"): {
            "globals": dict(UPDATED_PREVIOUS_RELEASE_SETTINGS),
            "socket": ("tcp", {"address": ("replicated", 6557)}),
            "replication": "slave",
        },
        SiteId("unreplicated"): {
            "globals": previous_release_settings(),
            "socket": ("tcp", {"address": ("unreplicated", 6557)}),
            "replication": None,
        },
    }
