#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import Checkbox
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSiteManagement

CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT = "site_piggyback_hub"


def register(config_variable_registry: ConfigVariableRegistry) -> None:
    config_variable_registry.register(ConfigVariableSitePiggybackHub)


def piggyback_hub_config_value_spec() -> Checkbox:
    return Checkbox(
        title=_("Enable piggyback-hub"),
        help=_("Enable the piggyback-hub to send/receive piggyback data to/from other sites."),
        default_value=False,
    )


ConfigVariableSitePiggybackHub = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    domain=ConfigDomainOMD,
    ident=CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT,
    valuespec=lambda: piggyback_hub_config_value_spec(),
)
