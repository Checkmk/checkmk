#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest
from pytest_mock import MockerFixture

from cmk.gui.plugins.wato.check_mk_configuration import ConfigVariableGroupUserInterface
from cmk.gui.plugins.watolib.utils import ConfigVariable, ConfigVariableRegistry
from cmk.gui.valuespec import TextInput, Transform
from cmk.gui.watolib.config_domains import ConfigDomainGUI

from cmk.update_config.plugins.actions import global_settings


def test_update_global_config_transform_values(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Disable variable filtering by known Checkmk variables
    mocker.patch.object(
        global_settings, "filter_unknown_settings", lambda global_config: global_config
    )

    class ConfigVariableKey(ConfigVariable):
        def group(self) -> type[ConfigVariableGroupUserInterface]:
            return ConfigVariableGroupUserInterface

        def domain(self) -> type[ConfigDomainGUI]:
            return ConfigDomainGUI

        def ident(self) -> str:
            return "key"

        def valuespec(self) -> Transform:
            return Transform(TextInput(), forth=lambda x: "new" if x == "old" else x)

    registry = ConfigVariableRegistry()
    registry.register(ConfigVariableKey)
    monkeypatch.setattr(global_settings, "config_variable_registry", registry)

    assert global_settings.update_global_config(logging.getLogger(), {"key": "old"}) == {
        "key": "new"
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
