#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.plugins.wato as api_module  # astrein: disable=cmk-module-layer-violation
from cmk.gui.plugins.wato import datasource_programs  # astrein: disable=cmk-module-layer-violation
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersNetworking,
    RulespecGroupDatasourcePrograms,
)
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    HostRulespec,
    rulespec_registry,
)


def register() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by built-in and also 3rd party plugins.

    Our built-in plug-in have been changed to directly import from the .utils module. We add these
    old names to remain compatible with 3rd party plug-ins for now.

    What is registered here is what a *working* extension published on the Checkmk Exchange
    imports.

    In the moment we define an official plug-in API, we can drop this and require all plug-ins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    for name, value in (
        ("CheckParameterRulespecWithItem", CheckParameterRulespecWithItem),
        ("CheckParameterRulespecWithoutItem", CheckParameterRulespecWithoutItem),
        ("HostRulespec", HostRulespec),
        ("RulespecGroupCheckParametersApplications", RulespecGroupCheckParametersApplications),
        ("RulespecGroupCheckParametersDiscovery", RulespecGroupCheckParametersDiscovery),
        ("RulespecGroupCheckParametersNetworking", RulespecGroupCheckParametersNetworking),
        ("rulespec_registry", rulespec_registry),
    ):
        api_module.__dict__[name] = value

    datasource_programs.__dict__["RulespecGroupDatasourcePrograms"] = (
        RulespecGroupDatasourcePrograms
    )
