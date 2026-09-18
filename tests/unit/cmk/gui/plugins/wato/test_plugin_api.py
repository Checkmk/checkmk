#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.plugins.wato
import cmk.gui.plugins.wato.datasource_programs

pytestmark = pytest.mark.usefixtures("load_plugins")

# cmk.gui.wato._pre_21_plugin_api injects these by name, so nothing but this test notices when one
# of them disappears. Each is registered because an extension published on the Checkmk Exchange
# imports it from a plug-in that loads; the package named alongside is the one that asked, so
# whoever comes to drop a name can go and look at what it is for.

_API_MODULE_NAMES = (
    ("CheckParameterRulespecWithItem", "cmk-cisco-ucm, robotmk"),
    ("CheckParameterRulespecWithoutItem", "SonicWall, hpe_oneview, poe_switch"),
    ("HostRulespec", "cmk-cisco-ucm, hci_cluster, hpe_oneview, robotmk"),
    ("RulespecGroupCheckParametersApplications", "SonicWall, cmk-cisco-ucm, hpe_oneview, robotmk"),
    ("RulespecGroupCheckParametersDiscovery", "cmk-cisco-ucm, robotmk"),
    ("RulespecGroupCheckParametersNetworking", "poe_switch"),
    (
        "rulespec_registry",
        "SonicWall, cmk-cisco-ucm, hci_cluster, hpe_oneview, poe_switch, robotmk",
    ),
)

_DATASOURCE_PROGRAMS_NAMES = (("RulespecGroupDatasourcePrograms", "hpe_oneview"),)


@pytest.mark.parametrize(("name", "extensions"), _API_MODULE_NAMES)
def test_pre_21_plugin_api_names(name: str, extensions: str) -> None:
    assert name in cmk.gui.plugins.wato.__dict__, f"imported by {extensions}"


@pytest.mark.parametrize(("name", "extensions"), _DATASOURCE_PROGRAMS_NAMES)
def test_pre_21_datasource_programs_names(name: str, extensions: str) -> None:
    assert name in cmk.gui.plugins.wato.datasource_programs.__dict__, f"imported by {extensions}"
