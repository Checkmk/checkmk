#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk wide type definitions"""

import abc
import enum
import functools
import string
import sys
from typing import Any, Dict, Iterable, List, NewType, Optional, Set, Tuple, Union

HostName = str
HostAddress = str
HostgroupName = str
ServiceName = str
ServicegroupName = str
ContactgroupName = str
TimeperiodName = str
RawAgentData = bytes
RulesetName = str
RuleValue = Any  # TODO: Improve this type
RuleSpec = Dict[str, Any]  # TODO: Improve this type
Ruleset = List[RuleSpec]  # TODO: Improve this type
MetricName = str
CheckPluginName = str
InventoryPluginName = str
ActiveCheckPluginName = str
Item = Optional[str]
TagValue = str
Labels = Dict[str, str]
LabelSources = Dict[str, str]
TagID = str
TaggroupID = str
Tags = Dict[TagID, TagValue]
TagList = Set[TagValue]
TagGroups = Dict[TagID, TaggroupID]
HostNameConditions = Union[None, Dict[str, List[Union[Dict[str, str], str]]],
                           List[Union[Dict[str, str], str]]]
ServiceNameConditions = Union[None, Dict[str, List[Union[Dict[str, str], str]]],
                              List[Union[Dict[str, str], str]]]
CheckVariables = Dict[str, Any]
Seconds = int
Timestamp = int
TimeRange = Tuple[int, int]

ServiceState = int
HostState = int
ServiceDetails = str
ServiceAdditionalDetails = str
# TODO: Specify this  (see cmk/base/checking.py::_convert_perf_data)
Metric = List
ServiceCheckResult = Tuple[ServiceState, ServiceDetails, List[Metric]]

UserId = NewType("UserId", str)
EventRule = Dict[str, Any]  # TODO Improve this

AgentHash = NewType("AgentHash", str)
BakeryOpSys = NewType("BakeryOpSys", str)
AgentConfig = Dict[str, Any]  # TODO Split into more sub configs
BakeryHostName = Union[bool, None, HostName]

# TODO: TimeperiodSpec should really be a class or at least a NamedTuple! We
# can easily transform back and forth for serialization.
TimeperiodSpec = Dict[str, Union[str, List[Tuple[str, str]]]]


class ABCPluginName(abc.ABC):
    """Common class for all plugin names

    A plugin name must be a non-empty string consting only of letters A-z, digits
    and the underscore.
    """
    VALID_CHARACTERS = string.ascii_letters + '_' + string.digits

    @abc.abstractproperty
    def _legacy_naming_exceptions(self) -> Set[str]:
        """we allow to maintain a list of exceptions"""
        return set()

    def __init__(self, plugin_name, forbidden_names=None):
        # type: (str, Optional[Iterable[ABCPluginName]]) -> None
        self._value = plugin_name
        if plugin_name in self._legacy_naming_exceptions:
            return

        if not isinstance(plugin_name, str):
            raise TypeError("%s must initialized from str" % self.__class__.__name__)
        if not plugin_name:
            raise ValueError("%s initializer must not be empty" % self.__class__.__name__)

        for char in plugin_name:
            if char not in self.VALID_CHARACTERS:
                raise ValueError("invalid character for %s %r: %r" %
                                 (self.__class__.__name__, plugin_name, char))

        if forbidden_names and any(plugin_name == str(fn) for fn in forbidden_names):
            raise ValueError("duplicate plugin name: %r" % (plugin_name,))

    def __repr__(self):
        # type: () -> str
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def __str__(self):
        # type: () -> str
        return self._value

    def __eq__(self, other):
        # type: (Any) -> bool
        if not isinstance(other, self.__class__):
            raise TypeError("can only be compared with %s objects" % self.__class__)
        return self._value == other._value

    def __lt__(self, other):
        # type: (Any) -> bool
        if not isinstance(other, self.__class__):
            raise TypeError("Can only be compared with %s objects" % self.__class__)
        return self._value < other._value

    def __hash__(self):
        # type: () -> int
        return hash(type(self).__name__ + self._value)


@functools.total_ordering
class SectionName(ABCPluginName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()


# TODO (mo):
# At some point, we should have as different classes at least:
#   * SectionName
#   * ParsedSectionName
#   * CheckPluginName
#   * InventoryPluginName
#   * RulesetName
# The relation between the different plugins should be specified in the
# plugin definitions, s.t. things like 'PluginName(str(section_name))'
# should never be needed.
@functools.total_ordering
class PluginName(ABCPluginName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        """
        allow these names

        Unfortunately, we have some WATO rules that contain dots or dashes.
        In order not to break things, we allow those
        """
        return {
            'drbd.net', 'drbd.disk', 'drbd.stats', 'fileinfo-groups', 'hpux_snmp_cs.cpu',
            'j4p_performance.mem', 'j4p_performance.threads', 'j4p_performance.uptime',
            'j4p_performance.app_state', 'j4p_performance.app_sess', 'j4p_performance.serv_req',
            'sap_value-groups'
        }


class SourceType(enum.Enum):
    """Classification of management sources vs regular hosts"""
    HOST = "HOST"
    MANAGEMENT = "MANAGEMENT"


class OIDSpec:
    """Basic class for OID spec of the form ".1.2.3.4.5" or "2.3"
    """
    VALID_CHARACTERS = '.' + string.digits

    @classmethod
    def validate(cls, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("expected a non-empty string: %r" % (value,))
        if not value:
            raise ValueError("expected a non-empty string: %r" % (value,))

        invalid = ''.join(c for c in value if c not in cls.VALID_CHARACTERS)
        if invalid:
            raise ValueError("invalid characters in OID descriptor: %r" % invalid)

        if value.endswith('.'):
            raise ValueError("%r should not end with '.'" % (value,))

    def __init__(self, value: str) -> None:
        self.validate(value)
        self._value = value


# TODO: We should really parse our configuration file and use a
# class/NamedTuple, see above.
def timeperiod_spec_alias(timeperiod_spec: TimeperiodSpec, default: str = u"") -> str:
    alias = timeperiod_spec.get("alias", default)
    if isinstance(alias, str):
        return alias
    raise Exception("invalid timeperiod alias %r" % (alias,))


class EvalableFloat(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""
    def __str__(self):
        return super().__repr__()

    def __repr__(self) -> str:
        if self > sys.float_info.max:
            return '1e%d' % (sys.float_info.max_10_exp + 1)
        if self < -1 * sys.float_info.max:
            return '-1e%d' % (sys.float_info.max_10_exp + 1)
        return super().__repr__()
