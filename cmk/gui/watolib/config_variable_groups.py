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
from cmk.web.utils.icons import IconNames


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
    icon=IconNames.notifications,
    description=_l("Configures global notification system behavior"),
)


ConfigVariableGroupUserInterface = ConfigVariableGroup(
    title=_l("User interface"),
    sort_index=20,
    icon=IconNames.ui_component_library,
    description=_l("Configures broad GUI look, behavior, and performance"),
)


ConfigVariableGroupWATO = ConfigVariableGroup(
    title=_l("Setup"),
    sort_index=25,
    icon=IconNames.main_setup,
    description=_l("Configures behavior of the config workflow itself"),
)


ConfigVariableGroupSiteManagement = ConfigVariableGroup(
    title=_l("Site management"),
    sort_index=30,
    icon=IconNames.sites,
    description=_l("Configures distributed monitoring and site connection settings"),
)


ConfigVariableGroupSupport = ConfigVariableGroup(
    title=_l("Support"),
    sort_index=80,
    icon=IconNames.diagnostics,
    description=_l("Configures support and diagnostics properties"),
)


ConfigVariableGroupDeveloperTools = ConfigVariableGroup(
    title=_l("Developer tools"),
    sort_index=90,
    warning=_l(
        "These are internal settings used by Checkmk developers. "
        "Do not change them unless you know what you are doing. "
        "There is a high risk that using these features will break your Checkmk site. "
        "Any changes here will result in your Checkmk site no longer being officially supported."
    ),
    icon=IconNames.developer_resources,
    description=_l("Configures internal and experimental developer settings"),
)


ConfigVariableGroupAIFeatures = ConfigVariableGroup(
    title=_l("AI features"),
    sort_index=99,
    icon=IconNames.sparkle,
    description=_l("Configures the AI assistant and MCP server integration"),
)
