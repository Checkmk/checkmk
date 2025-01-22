#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.piggyback_hub.config_domain import ConfigDomainDistributedPiggyback
from cmk.gui.piggyback_hub.settings import (
    ConfigVariableEnable,
    ConfigVariableGroupDistributedPiggyback,
)
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
)


def register(
    config_domain_registry: ConfigDomainRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    config_variable_registry: ConfigVariableRegistry,
) -> None:
    config_domain_registry.register(ConfigDomainDistributedPiggyback())
    config_variable_group_registry.register(ConfigVariableGroupDistributedPiggyback)
    config_variable_registry.register(ConfigVariableEnable)
