#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Optional, Tuple

from cmk.utils.type_defs import CheckPluginName, Item, LegacyCheckParameters

from cmk.base.discovered_labels import DiscoveredServiceLabels

RulesetName = str
ServiceID = Tuple[CheckPluginName, Item]
CheckTable = Dict[ServiceID, 'Service']


class Service:
    __slots__ = ["_check_plugin_name", "_item", "_description", "_parameters", "_service_labels"]

    def __init__(
        self,
        check_plugin_name: CheckPluginName,
        item: Item,
        description: str,
        parameters: LegacyCheckParameters,
        service_labels: Optional[DiscoveredServiceLabels] = None,
    ) -> None:
        self._check_plugin_name = check_plugin_name
        self._item = item
        self._description = description
        self._service_labels = service_labels or DiscoveredServiceLabels()
        self._parameters = parameters

    @property
    def check_plugin_name(self) -> CheckPluginName:
        return self._check_plugin_name

    @property
    def item(self) -> Item:
        return self._item

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> LegacyCheckParameters:
        return self._parameters

    @property
    def service_labels(self) -> DiscoveredServiceLabels:
        return self._service_labels

    def id(self) -> ServiceID:
        return self.check_plugin_name, self.item

    def __lt__(self, other: Any) -> bool:
        """Allow to sort services

        Basically sort by id(). Unfortunately we have plugins with *AND* without
        items.
        """
        if not isinstance(other, Service):
            raise TypeError("Can only be compared with other Service objects")
        return (self.check_plugin_name, self.item or "") < (other.check_plugin_name, other.item or
                                                            "")

    def __eq__(self, other: Any) -> bool:
        """Is used during service discovery list computation to detect and replace duplicates
        For this the parameters and similar need to be ignored."""
        if not isinstance(other, Service):
            raise TypeError("Can only be compared with other Service objects")
        return self.id() == other.id()

    def __hash__(self) -> int:
        """Is used during service discovery list computation to detect and replace duplicates
        For this the parameters and similar need to be ignored."""
        return hash(self.id())

    def __repr__(self) -> str:
        return "Service(check_plugin_name=%r, item=%r, description=%r, parameters=%r, service_labels=%r)" % (
            self._check_plugin_name, self._item, self._description, self._parameters,
            self._service_labels)

    def dump_autocheck(self) -> str:
        return "{'check_plugin_name': %r, 'item': %r, 'parameters': %r, 'service_labels': %r}" % (
            str(self.check_plugin_name),
            self.item,
            self.parameters,
            self.service_labels.to_dict(),
        )
