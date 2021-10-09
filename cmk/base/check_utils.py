#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Final, Mapping, Optional, Tuple

from cmk.utils.type_defs import CheckPluginName, Item, LegacyCheckParameters

from cmk.base.discovered_labels import ServiceLabel

ServiceID = Tuple[CheckPluginName, Item]
CheckTable = Dict[ServiceID, "Service"]


class Service:
    __slots__ = ["check_plugin_name", "item", "description", "parameters", "service_labels"]

    def __init__(
        self,
        check_plugin_name: CheckPluginName,
        item: Item,
        description: str,
        parameters: LegacyCheckParameters,
        service_labels: Optional[Mapping[str, ServiceLabel]] = None,
    ) -> None:
        self.check_plugin_name: Final = check_plugin_name
        self.item: Final = item
        self.description: Final = description
        self.parameters: Final = parameters
        self.service_labels: Final = service_labels or {}

    def id(self) -> ServiceID:
        return self.check_plugin_name, self.item

    def __lt__(self, other: Any) -> bool:
        """Allow to sort services

        Basically sort by id(). Unfortunately we have plugins with *AND* without
        items.
        """
        if not isinstance(other, Service):
            raise TypeError("Can only be compared with other Service objects")
        return (self.check_plugin_name, self.item or "") < (
            other.check_plugin_name,
            other.item or "",
        )

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
            self.check_plugin_name,
            self.item,
            self.description,
            self.parameters,
            self.service_labels,
        )


class AutocheckService(Service):
    """Just a little bit more specific than any service

    Autocheck services do not compute the effectice parameters, but only contain the discovered
    ones.
    More importantly: an general 'Service' instance may not be dumped into the autochecks file.
    """

    def dump_autocheck(self) -> str:
        return "{'check_plugin_name': %r, 'item': %r, 'parameters': %r, 'service_labels': %r}" % (
            str(self.check_plugin_name),
            self.item,
            self.parameters,
            {l.name: l.value for l in self.service_labels.values()},
        )
