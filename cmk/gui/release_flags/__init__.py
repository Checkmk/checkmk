#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.release_flags import global_config
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
)


def register(
    config_domain_registry: ConfigDomainRegistry,
    config_variable_registry: ConfigVariableRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
) -> None:
    config_domain_registry.register(global_config.ConfigDomainReleaseFlags())

    # The group and its config variables are generated from the flags declared on
    # ReleaseFlagConfig. When no flags are declared (e.g. on master) there is
    # nothing to show, so we skip registering an empty settings group.
    if global_config.release_flag_config_variables:
        config_variable_group_registry.register(global_config.ConfigVariableGroupReleaseFlags)
        for config_variable in global_config.release_flag_config_variables:
            config_variable_registry.register(config_variable)
