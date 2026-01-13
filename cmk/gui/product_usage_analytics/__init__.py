#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.product_usage_analytics import global_config
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
    config_domain_registry.register(global_config.ConfigDomainProductUsageAnalytics)
    config_variable_group_registry.register(global_config.ConfigVariableGroupProductUsageAnalytics)
    config_variable_registry.register(global_config.ConfigVariableProductUsageAnalytics)
