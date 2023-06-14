#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for computing the table of checks of hosts."""

import enum
from collections.abc import Iterable, Iterator, Mapping
from typing import NamedTuple

from cmk.utils.labels import ServiceLabel
from cmk.utils.type_defs import Item, LegacyCheckParameters, ServiceName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.parameters import TimespecificParameters


class ServiceID(NamedTuple):
    name: CheckPluginName
    item: Item


class FilterMode(enum.Enum):
    NONE = enum.auto()
    INCLUDE_CLUSTERED = enum.auto()


class ConfiguredService(NamedTuple):
    """A service with all information derived from the config"""

    check_plugin_name: CheckPluginName
    item: Item
    description: ServiceName
    parameters: TimespecificParameters
    # Explicitly optional b/c enforced services don't have disocvered params.
    discovered_parameters: LegacyCheckParameters | None
    service_labels: Mapping[str, ServiceLabel]
    is_enforced: bool

    def id(self) -> ServiceID:
        return ServiceID(self.check_plugin_name, self.item)

    def sort_key(self) -> ServiceID:
        """Allow to sort services

        Basically sort by id(). Unfortunately we have plugins with *AND* without
        items.
        """
        return ServiceID(self.check_plugin_name, self.item or "")


class HostCheckTable(Mapping[ServiceID, ConfiguredService]):
    def __init__(
        self,
        *,
        services: Iterable[ConfiguredService],
    ) -> None:
        self._data = {s.id(): s for s in services}

    def __getitem__(self, key: ServiceID) -> ConfiguredService:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[ServiceID]:
        return iter(self._data)

    def needed_check_names(self) -> set[CheckPluginName]:
        return {s.check_plugin_name for s in self.values()}
