#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple, Optional, Tuple

from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import CheckPluginName, Item, LegacyCheckParameters, ServiceName

from cmk.base.discovered_labels import ServiceLabel

ServiceID = Tuple[CheckPluginName, Item]


class ConfiguredService(NamedTuple):
    """A service with all information derived from the config"""

    check_plugin_name: CheckPluginName
    item: Item
    description: ServiceName
    parameters: TimespecificParameters
    # Explicitly optional b/c enforced services don't have disocvered params.
    discovered_parameters: Optional[LegacyCheckParameters]
    service_labels: Mapping[str, ServiceLabel]

    def id(self) -> ServiceID:
        return self.check_plugin_name, self.item

    def sort_key(self) -> Tuple[CheckPluginName, str]:
        """Allow to sort services

        Basically sort by id(). Unfortunately we have plugins with *AND* without
        items.
        """
        return self.check_plugin_name, self.item or ""
