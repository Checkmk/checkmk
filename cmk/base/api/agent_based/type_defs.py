#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Type definitions

Some of these are exposed in the API, some are not.
"""
from collections.abc import Mapping
from abc import ABC
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Literal,
    MutableMapping,
    NamedTuple,
    Optional,
    Set,
    Union,
)
import pprint

from cmk.utils.type_defs import (
    CheckPluginName,
    ParsedSectionName,
    RuleSetName,
    SectionName,
)
from cmk.snmplib.type_defs import SNMPDetectSpec, SNMPRuleDependentDetectSpec, SNMPTree

from cmk.base.discovered_labels import HostLabel


class ABCComparable(ABC):
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %s to %s" %
                            (self.__class__.__name__, other.__class__.__name__))

        return self.__dict__ == other.__dict__


class ABCCheckGenerated(ABCComparable):
    """Abstract class for everything a check function may yield"""


class ABCDiscoveryGenerated(ABCComparable):
    """Abstract class for everything a discovery function may yield"""


class Parameters(Mapping):
    """Parameter objects are used to pass parameters to plugin functions"""
    def __init__(self, data):
        if not isinstance(data, dict):
            raise TypeError("Parameters expected dict, got %r" % (data,))
        self._data = dict(data)

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        # use pformat to be testable.
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self._data))


AgentStringTable = List[List[str]]
AgentParseFunction = Callable[[AgentStringTable], Any]
CheckGenerator = Generator[ABCCheckGenerated, None, None]
CheckFunction = Callable[..., CheckGenerator]

DiscoveryRuleSetType = Literal["merged", "all"]

DiscoveryGenerator = Generator[ABCDiscoveryGenerated, None, None]
DiscoveryFunction = Callable[..., DiscoveryGenerator]

HostLabelGenerator = Generator[HostLabel, None, None]
HostLabelFunction = Callable[..., HostLabelGenerator]

SNMPStringTable = List[List[List[str]]]
SNMPStringByteTable = List[List[List[Union[str, List[int]]]]]
SNMPParseFunction = Union[Callable[[SNMPStringTable], Any], Callable[[SNMPStringByteTable], Any],]
CheckPlugin = NamedTuple(
    "CheckPlugin",
    [
        ("name", CheckPluginName),
        ("sections", List[ParsedSectionName]),
        ("service_name", str),
        ("discovery_function", DiscoveryFunction),
        ("discovery_default_parameters", Optional[Dict[str, Any]]),
        ("discovery_ruleset_name", Optional[RuleSetName]),
        ("discovery_ruleset_type", DiscoveryRuleSetType),
        ("check_function", CheckFunction),
        ("check_default_parameters", Optional[Dict[str, Any]]),
        ("check_ruleset_name", Optional[RuleSetName]),
        ("cluster_check_function", CheckFunction),
        ("module", Optional[str]),  # not available for auto migrated plugins.
    ],
)

AgentSectionPlugin = NamedTuple(
    "AgentSectionPlugin",
    [
        ("name", SectionName),
        ("parsed_section_name", ParsedSectionName),
        ("parse_function", AgentParseFunction),
        ("host_label_function", HostLabelFunction),
        ("supersedes", Set[SectionName]),
        ("module", Optional[str]),  # not available for auto migrated plugins.
    ],
)

SNMPSectionPlugin = NamedTuple(
    "SNMPSectionPlugin",
    [
        ("name", SectionName),
        ("parsed_section_name", ParsedSectionName),
        ("parse_function", SNMPParseFunction),
        ("host_label_function", HostLabelFunction),
        ("supersedes", Set[SectionName]),
        ("detect_spec", SNMPDetectSpec),
        ("trees", List[SNMPTree]),
        ("module", Optional[str]),  # not available for auto migrated plugins.
        # This attribute is not an official part of the API and setting it requires explicit API
        # violations. It is used for dynamically computing the used detection specifications based
        # on user-defined discovery rules. This is for example needed by some interface checks.
        ("rule_dependent_detect_spec", Optional[SNMPRuleDependentDetectSpec]),
    ],
)

SectionPlugin = Union[AgentSectionPlugin, SNMPSectionPlugin]

ValueStore = MutableMapping[str, Any]
