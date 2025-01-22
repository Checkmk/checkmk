#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.piggyback_hub.config_domain import ConfigDomainDistributedPiggyback
from cmk.gui.valuespec import Checkbox, ValueSpec
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, ConfigVariable, ConfigVariableGroup


class ConfigVariableGroupDistributedPiggyback(ConfigVariableGroup):
    def title(self) -> str:
        return _("Distributed piggyback")

    def sort_index(self) -> int:
        return 37


class ConfigVariableEnable(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupDistributedPiggyback

    def domain(self) -> ABCConfigDomain:
        return ConfigDomainDistributedPiggyback()

    def ident(self) -> str:
        return "piggyback_hub_enabled"

    def valuespec(self) -> ValueSpec:
        return Checkbox(
            title=_("Enable distributed piggyback"),
            help=_(
                "By disabling this option, piggyback data won't be distributed to or received from other sites."
                "Piggyback data received by a host from this site can still be used."
            ),
            default_value=True,
        )
