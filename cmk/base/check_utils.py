#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# .------------------------------------------------------------------------.
# |                ____ _               _        __  __ _  __              |
# |               / ___| |__   ___  ___| | __   |  \/  | |/ /              |
# |              | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
# |              | |___| | | |  __/ (__|   <    | |  | | . \               |
# |               \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
# |                                        |_____|                         |
# |             _____       _                       _                      |
# |            | ____|_ __ | |_ ___ _ __ _ __  _ __(_)___  ___             |
# |            |  _| | '_ \| __/ _ \ '__| '_ \| '__| / __|/ _ \            |
# |            | |___| | | | ||  __/ |  | |_) | |  | \__ \  __/            |
# |            |_____|_| |_|\__\___|_|  | .__/|_|  |_|___/\___|            |
# |                                     |_|                                |
# |                     _____    _ _ _   _                                 |
# |                    | ____|__| (_) |_(_) ___  _ __                      |
# |                    |  _| / _` | | __| |/ _ \| '_ \                     |
# |                    | |__| (_| | | |_| | (_) | | | |                    |
# |                    |_____\__,_|_|\__|_|\___/|_| |_|                    |
# |                                                                        |
# | mathias-kettner.com                                 mathias-kettner.de |
# '------------------------------------------------------------------------'
#  This file is part of the Check_MK Enterprise Edition (CEE).
#  Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
#  Distributed under the Check_MK Enterprise License.
#
#  You should have  received  a copy of the Check_MK Enterprise License
#  along with Check_MK. If not, email to mk@mathias-kettner.de
#  or write to the postal address provided at www.mathias-kettner.de

from typing import (  # pylint: disable=unused-import
    TYPE_CHECKING, Union, TypeVar, Iterable, Text, Optional, Dict, Tuple, Any, List, NoReturn,
)

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import Item, CheckPluginName  # pylint: disable=unused-import

import cmk.base
from cmk.base.discovered_labels import DiscoveredServiceLabels
from cmk.base.utils import HostName

if TYPE_CHECKING:
    from cmk.base.snmp_utils import (  # pylint: disable=unused-import
        RawSNMPData, SNMPSections, PersistedSNMPSections, SNMPSectionContent,
    )

CheckParameters = Union[None, Dict, Tuple, List, str]
RulesetName = str
ServiceState = int
HostState = int
ServiceDetails = Text
ServiceAdditionalDetails = Text
# TODO: Specify this  (see cmk/base/checking.py::_convert_perf_data)
Metric = List
ServiceCheckResult = Tuple[ServiceState, ServiceDetails, List[Metric]]

RawAgentData = bytes

SectionName = str
SectionCacheInfo = Dict[SectionName, Tuple[int, int]]

AgentSectionContent = List[List[Text]]
PersistedAgentSection = Tuple[int, int, AgentSectionContent]
PersistedAgentSections = Dict[SectionName, PersistedAgentSection]
AgentSections = Dict[SectionName, AgentSectionContent]

PiggybackRawData = Dict[HostName, List[bytes]]
ParsedSectionContent = Any
FinalSectionContent = Optional[Union[ParsedSectionContent, List[ParsedSectionContent]]]

AbstractSectionContent = Union[AgentSectionContent, "SNMPSectionContent"]
AbstractRawData = Union[RawAgentData, "RawSNMPData"]
AbstractSections = Union[AgentSections, "SNMPSections"]
AbstractPersistedSections = Union[PersistedAgentSections, "PersistedSNMPSections"]

BoundedAbstractRawData = TypeVar("BoundedAbstractRawData", bound=AbstractRawData)
BoundedAbstractSectionContent = TypeVar("BoundedAbstractSectionContent",
                                        bound=AbstractSectionContent)
BoundedAbstractSections = TypeVar("BoundedAbstractSections", bound=AbstractSections)
BoundedAbstractPersistedSections = TypeVar("BoundedAbstractPersistedSections",
                                           bound=AbstractPersistedSections)


class Service(object):
    __slots__ = ["_check_plugin_name", "_item", "_description", "_parameters", "_service_labels"]

    def __init__(self, check_plugin_name, item, description, parameters, service_labels=None):
        # type: (CheckPluginName, Item, Text, CheckParameters, DiscoveredServiceLabels) -> None
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
        # type: () -> Text
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
        # type: (CheckPluginName, Item, Text, CheckParameters, DiscoveredServiceLabels) -> None
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


def section_name_of(check_plugin_name):
    # type: (str) -> str
    return check_plugin_name.split(".")[0]


def is_snmp_check(check_plugin_name):
    # type: (str) -> bool
    cache = cmk.base.runtime_cache.get_dict("is_snmp_check")
    try:
        return cache[check_plugin_name]
    except KeyError:
        snmp_checks = cmk.base.runtime_cache.get_set("check_type_snmp")
        result = section_name_of(check_plugin_name) in snmp_checks
        cache[check_plugin_name] = result
        return result


def is_tcp_check(check_plugin_name):
    # type: (str) -> bool
    cache = cmk.base.runtime_cache.get_dict("is_tcp_check")
    try:
        return cache[check_plugin_name]
    except KeyError:
        tcp_checks = cmk.base.runtime_cache.get_set("check_type_tcp")
        result = section_name_of(check_plugin_name) in tcp_checks
        cache[check_plugin_name] = result
        return result
