#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Final, Generic, Mapping, Optional, Sequence, Tuple, TypeVar, Union

from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import CheckPluginName, Item, LegacyCheckParameters

from cmk.base.discovered_labels import ServiceLabel

ServiceID = Tuple[CheckPluginName, Item]
CheckTable = Dict[ServiceID, "Service"]


_Params = TypeVar("_Params", bound=Union[LegacyCheckParameters, TimespecificParameters])


class Service(Generic[_Params]):
    __slots__ = ["check_plugin_name", "item", "description", "parameters", "service_labels"]

    def __init__(
        self,
        check_plugin_name: CheckPluginName,
        item: Item,
        description: str,
        parameters: _Params,
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


class AutocheckService(Service[LegacyCheckParameters]):
    """Just a little bit more specific than any service

    Autocheck services do not compute the effectice parameters, but only contain the discovered
    ones.
    More importantly: an general 'Service' instance may not be dumped into the autochecks file.
    """


_TService = TypeVar("_TService", bound=Service)


def deduplicate_autochecks(autochecks: Sequence[_TService]) -> Sequence[_TService]:
    """Cleanup duplicates

    (in particular versions pre 1.6.0p8 may have introduced some in the autochecks file)

    The first service is kept:

    >>> deduplicate_autochecks([
    ...    AutocheckService(CheckPluginName('a'), None, "desctiption 1", None),
    ...    AutocheckService(CheckPluginName('a'), None, "description 2", None),
    ... ])[0].description
    'desctiption 1'

    """
    return list({a.id(): a for a in reversed(autochecks)}.values())
