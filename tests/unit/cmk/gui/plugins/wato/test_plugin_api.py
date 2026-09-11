#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.plugins.wato
import cmk.gui.plugins.wato.datasource_programs
import cmk.gui.wato

pytestmark = pytest.mark.usefixtures("load_plugins")

# cmk.gui.wato._pre_21_plugin_api injects these by name into the plug-in namespaces. Since it
# resolves them via __dict__ lookups, nothing but this test notices when one of the underlying
# re-exports disappears.
#
# Pinned here is what published extensions actually import, not everything that gets injected:
# the names below are the ones the packages on the Checkmk Exchange reach for, so breaking one
# breaks a package somebody is running. The rest of the injected surface is unpinned on purpose
# -- a test over names nobody imports would only record that they exist.

_API_MODULE_NAMES = (
    "CheckParameterRulespecWithItem",
    "CheckParameterRulespecWithoutItem",
    "HostRulespec",
    "NotificationParameter",
    "notification_parameter_registry",
    "RulespecGroupCheckParametersApplications",
    "RulespecGroupCheckParametersDiscovery",
    "RulespecGroupCheckParametersNetworking",
    "rulespec_registry",
)

_DATASOURCE_PROGRAMS_NAMES = ("RulespecGroupDatasourcePrograms",)

_SETUP_MODULE_NAMES = ("RulespecGroupActiveChecks",)


@pytest.mark.parametrize("name", _API_MODULE_NAMES)
def test_pre_21_plugin_api_names(name: str) -> None:
    assert name in cmk.gui.plugins.wato.__dict__


@pytest.mark.parametrize("name", _DATASOURCE_PROGRAMS_NAMES)
def test_pre_21_datasource_programs_names(name: str) -> None:
    assert name in cmk.gui.plugins.wato.datasource_programs.__dict__


@pytest.mark.parametrize("name", _SETUP_MODULE_NAMES)
def test_pre_21_setup_module_names(name: str) -> None:
    assert name in cmk.gui.wato.__dict__
