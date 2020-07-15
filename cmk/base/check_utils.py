#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Optional, Tuple, TypeVar, Union

from cmk.utils.check_utils import section_name_of
from cmk.utils.type_defs import CheckPluginNameStr, HostName, Item, RawAgentData, SectionName

from cmk.snmplib.type_defs import (
    SNMPPersistedSections,
    SNMPRawData,
    SNMPSectionContent,
    SNMPSections,
)

from cmk.base.caching import runtime_cache as _runtime_cache
from cmk.base.discovered_labels import DiscoveredServiceLabels

LegacyCheckParameters = Union[None, Dict, Tuple, List, str]
RulesetName = str

SectionCacheInfo = Dict[SectionName, Tuple[int, int]]

AgentSectionContent = List[List[str]]
PersistedAgentSection = Tuple[int, int, AgentSectionContent]
PersistedAgentSections = Dict[SectionName, PersistedAgentSection]
AgentSections = Dict[SectionName, AgentSectionContent]

PiggybackRawData = Dict[HostName, List[bytes]]
ParsedSectionContent = Any
FinalSectionContent = Union[None, ParsedSectionContent, List[ParsedSectionContent]]

AbstractSectionContent = Union[AgentSectionContent, SNMPSectionContent]
AbstractRawData = Union[RawAgentData, SNMPRawData]
AbstractSections = Union[AgentSections, SNMPSections]
AbstractPersistedSections = Union[PersistedAgentSections, SNMPPersistedSections]

BoundedAbstractRawData = TypeVar("BoundedAbstractRawData", bound=AbstractRawData)
BoundedAbstractSectionContent = TypeVar("BoundedAbstractSectionContent",
                                        bound=AbstractSectionContent)
BoundedAbstractSections = TypeVar("BoundedAbstractSections", bound=AbstractSections)
BoundedAbstractPersistedSections = TypeVar("BoundedAbstractPersistedSections",
                                           bound=AbstractPersistedSections)

ServiceID = Tuple[CheckPluginNameStr, Item]
CheckTable = Dict[ServiceID, 'Service']


class Service:
    __slots__ = ["_check_plugin_name", "_item", "_description", "_parameters", "_service_labels"]

    def __init__(
        self,
        check_plugin_name: CheckPluginNameStr,
        item: Item,
        description: str,
        parameters: LegacyCheckParameters,
        service_labels: DiscoveredServiceLabels = None,
    ) -> None:
        self._check_plugin_name = check_plugin_name
        self._item = item
        self._description = description
        self._service_labels = service_labels or DiscoveredServiceLabels()
        self._parameters = parameters

    @property
    def check_plugin_name(self) -> CheckPluginNameStr:
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
        return "Service(check_plugin_name=%r, item=%r, description=%r, parameters=%r, service_lables=%r)" % (
            self._check_plugin_name, self._item, self._description, self._parameters,
            self._service_labels)

    def dump_autocheck(self) -> str:
        return "{'check_plugin_name': %r, 'item': %r, 'parameters': %r, 'service_labels': %r}" % (
            self.check_plugin_name,
            self.item,
            self.parameters,
            self.service_labels.to_dict(),
        )


def is_snmp_check(check_plugin_name: str) -> bool:
    cache = _runtime_cache.get_dict("is_snmp_check")
    try:
        return cache[check_plugin_name]
    except KeyError:
        snmp_checks = _runtime_cache.get_set("check_type_snmp")
        result = section_name_of(check_plugin_name) in snmp_checks
        cache[check_plugin_name] = result
        return result


# TODO (mo): *consider* using the type aliases.
def get_default_parameters(
    check_info_dict: Dict[str, Any],
    factory_settings: Dict[str, Dict[str, Any]],
    check_context: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """compute default parameters"""
    params_variable_name = check_info_dict.get("default_levels_variable")
    if not params_variable_name:
        return None

    # factory_settings
    fs_parameters = factory_settings.get(params_variable_name, {})

    # global scope of check context
    gs_parameters = check_context.get(params_variable_name)

    return {
        **fs_parameters,
        **gs_parameters,
    } if isinstance(gs_parameters, dict) else fs_parameters
