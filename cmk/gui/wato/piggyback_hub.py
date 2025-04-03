#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import Checkbox
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigVariable,
    ConfigVariableGroup,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSiteManagement


def register(config_variable_registry: ConfigVariableRegistry) -> None:
    config_variable_registry.register(ConfigVariableSitePiggybackHub)


class ConfigVariableSitePiggybackHub(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupSiteManagement

    def domain(self) -> ABCConfigDomain:
        return ConfigDomainOMD()

    def ident(self) -> str:
        return "site_piggyback_hub"

    def valuespec(self) -> Checkbox:
        return Checkbox(
            title=_("Enable piggyback-hub"),
            help=_("Enable the piggyback-hub to send/receive piggyback data to/from other sites."),
            default_value=False,
        )
