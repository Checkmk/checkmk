#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Type definitions

Some of these are exposed in the API, some are not.
"""
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Union,
)

from cmk.utils.type_defs import CheckPluginName, ParsedSectionName, RuleSetName, SectionName
from cmk.snmplib.type_defs import SNMPDetectSpec, SNMPTree

from cmk.base.discovered_labels import HostLabel


class ABCCheckGenerated:
    """Abstract class for everything a check function may yield"""


class ABCDiscoveryGenerated:
    """Abstract class for everything a discovery function may yield"""


AgentStringTable = List[List[str]]
AgentParseFunction = Callable[[AgentStringTable], Any]

CheckGenerator = Generator[ABCCheckGenerated, None, None]
CheckFunction = Callable[..., CheckGenerator]

DISCOVERY_RULESET_TYPE_CHOICES = ("merged", "all")
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
        ("discovery_default_parameters", Dict[str, Any]),
        ("discovery_ruleset_name", Optional[RuleSetName]),
        ("discovery_ruleset_type", DiscoveryRuleSetType),
        ("check_function", CheckFunction),
        ("check_default_parameters", Dict[str, Any]),
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
        ("supersedes", List[SectionName]),
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
        ("supersedes", List[SectionName]),
        ("detect_spec", SNMPDetectSpec),
        ("trees", List[SNMPTree]),
        ("module", Optional[str]),  # not available for auto migrated plugins.
    ],
)

SectionPlugin = Union[AgentSectionPlugin, SNMPSectionPlugin]
