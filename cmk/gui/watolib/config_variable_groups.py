#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Register the built-in global setting configuration variable groups"""

from cmk.gui.i18n import _l
from cmk.gui.watolib.config_domain_name import (
    ConfigVariableGroup,
    ConfigVariableGroupRegistry,
)


def register(config_variable_group_registry: ConfigVariableGroupRegistry) -> None:
    config_variable_group_registry.register(ConfigVariableGroupNotifications)
    config_variable_group_registry.register(ConfigVariableGroupUserInterface)
    config_variable_group_registry.register(ConfigVariableGroupWATO)
    config_variable_group_registry.register(ConfigVariableGroupSiteManagement)
    config_variable_group_registry.register(ConfigVariableGroupSupport)
    config_variable_group_registry.register(ConfigVariableGroupDeveloperTools)


ConfigVariableGroupNotifications = ConfigVariableGroup(
    title=_l("Notifications"),
    sort_index=15,
)


ConfigVariableGroupUserInterface = ConfigVariableGroup(
    title=_l("User interface"),
    sort_index=20,
)


ConfigVariableGroupWATO = ConfigVariableGroup(
    title=_l("Setup"),
    sort_index=25,
)


ConfigVariableGroupSiteManagement = ConfigVariableGroup(
    title=_l("Site management"),
    sort_index=30,
)


ConfigVariableGroupSupport = ConfigVariableGroup(
    title=_l("Support"),
    sort_index=80,
)


ConfigVariableGroupDeveloperTools = ConfigVariableGroup(
    title=_l("Developer Tools"),
    sort_index=90,
    warning=_l(
        "These are internal settings used by Checkmk developers. "
        "Do not change them unless you know what you are doing. "
        "There is a high risk that using these features will break your Checkmk site. "
        "Any changes here will result in your Checkmk site no longer being officially supported."
    ),
)
