#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, NoReturn, Tuple, TypeVar, Union

from cmk.utils.check_utils import section_name_of
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName, HostName, Item, RawAgentData, SectionName

from cmk.snmplib.type_defs import (
    SNMPPersistedSections,
    SNMPRawData,
    SNMPSectionContent,
    SNMPSections,
)

from cmk.base.caching import runtime_cache as _runtime_cache
from cmk.base.discovered_labels import DiscoveredServiceLabels

CheckParameters = Union[None, Dict, Tuple, List, str]
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


class Service:
    __slots__ = ["_check_plugin_name", "_item", "_description", "_parameters", "_service_labels"]

    def __init__(self, check_plugin_name, item, description, parameters, service_labels=None):
        # type: (CheckPluginName, Item, str, CheckParameters, DiscoveredServiceLabels) -> None
        self._check_plugin_name = check_plugin_name
        self._item = item
        self._description = description
        self._parameters = parameters
        self._service_labels = service_labels or DiscoveredServiceLabels()

    @property
    def check_plugin_name(self):
        # type: () -> CheckPluginName
        return self._check_plugin_name

    @property
    def item(self):
        # type: () -> Item
        return self._item

    @property
    def description(self):
        # type: () -> str
        return self._description

    @property
    def parameters(self):
        # type: () -> CheckParameters
        return self._parameters

    @property
    def service_labels(self):
        # type: () -> DiscoveredServiceLabels
        return self._service_labels

    def __eq__(self, other):
        # type: (Any) -> bool
        """Is used during service discovery list computation to detect and replace duplicates
        For this the parameters and similar need to be ignored."""
        if not isinstance(other, Service):
            raise TypeError("Can only be compared with other Service objects")
        return self.check_plugin_name == other.check_plugin_name and self.item == other.item

    def __hash__(self):
        # type: () -> int
        """Is used during service discovery list computation to detect and replace duplicates
        For this the parameters and similar need to be ignored."""
        return hash((self.check_plugin_name, self.item))

    def __repr__(self):
        # type: () -> str
        return "Service(check_plugin_name=%r, item=%r, description=%r, parameters=%r, service_lables=%r)" % (
            self._check_plugin_name, self._item, self._description, self._parameters,
            self._service_labels)


CheckTable = Dict[Tuple[CheckPluginName, Item], Service]


class DiscoveredService(Service):
    __slots__ = []  # type: List[str]
    """Special form of Service() which holds the unresolved textual representation of the check parameters"""
    def __init__(self,
                 check_plugin_name,
                 item,
                 description,
                 parameters_unresolved,
                 service_labels=None):
        # type: (CheckPluginName, Item, str, CheckParameters, DiscoveredServiceLabels) -> None
        super(DiscoveredService, self).__init__(check_plugin_name=check_plugin_name,
                                                item=item,
                                                description=description,
                                                parameters=parameters_unresolved,
                                                service_labels=service_labels)

    @property
    def parameters(self):
        # type: () -> NoReturn
        raise MKGeneralException(
            "Can not get the resolved parameters from a DiscoveredService object")

    @property
    def parameters_unresolved(self):
        # type: () -> CheckParameters
        """Returns the unresolved check parameters discovered for this service

        The reason for this hack is some old check API behaviour: A check may return the name of
        a default levels variable (as string), for example "cpu_utilization_default_levels".
        The user is allowed to override the value of this variable in his configuration and
        the check needs to evaluate this variable after config loading or during check
        execution. The parameter must not be resolved during discovery.
        """
        return self._parameters

    def __repr__(self):
        # type: () -> str
        return "DiscoveredService(check_plugin_name=%r, item=%r, description=%r, parameters_unresolved=%r, service_lables=%r)" % (
            self._check_plugin_name, self._item, self._description, self._parameters,
            self._service_labels)


DiscoveredCheckTable = Dict[Tuple[CheckPluginName, Item], DiscoveredService]


def is_snmp_check(check_plugin_name):
    # type: (str) -> bool
    cache = _runtime_cache.get_dict("is_snmp_check")
    try:
        return cache[check_plugin_name]
    except KeyError:
        snmp_checks = _runtime_cache.get_set("check_type_snmp")
        result = section_name_of(check_plugin_name) in snmp_checks
        cache[check_plugin_name] = result
        return result
