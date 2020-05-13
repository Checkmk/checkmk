#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk wide type definitions"""

from typing import Union, NamedTuple, NewType, Any, Text, Optional, Dict, Set, List, Tuple

HostName = str
HostAddress = str
HostgroupName = str
ServiceName = Text
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
Item = Optional[Text]
TagValue = str
Labels = Dict[Text, Text]
LabelSources = Dict[Text, str]
TagID = str
TaggroupID = str
Tags = Dict[TagID, TagValue]
TagList = Set[TagValue]
TagGroups = Dict[TagID, TaggroupID]
HostNameConditions = Union[None, Dict[str, List[Union[Dict[str, str], str]]],
                           List[Union[Dict[str, str], str]]]
ServiceNameConditions = Union[None, Dict[str, List[Union[Dict[str, Text], Text]]],
                              List[Union[Dict[str, Text], Text]]]
CheckVariables = Dict[str, Any]
Seconds = int
Timestamp = int
TimeRange = Tuple[int, int]

ServiceState = int
HostState = int
ServiceDetails = Text
ServiceAdditionalDetails = Text
# TODO: Specify this  (see cmk/base/checking.py::_convert_perf_data)
Metric = List
ServiceCheckResult = Tuple[ServiceState, ServiceDetails, List[Metric]]

UserId = NewType("UserId", Text)
EventRule = Dict[str, Any]  # TODO Improve this

AgentHash = NewType("AgentHash", str)
BakeryOpSys = NewType("BakeryOpSys", str)
AgentConfig = Dict[str, Any]  # TODO Split into more sub configs
BakeryHostName = Union[bool, None, HostName]

# TODO: TimeperiodSpec should really be a class or at least a NamedTuple! We
# can easily transform back and forth for serialization.
TimeperiodSpec = Dict[str, Union[Text, List[Tuple[str, str]]]]

ContextName = str
DecodedString = Text
DecodedBinary = List[int]
DecodedValues = Union[DecodedString, DecodedBinary]
SNMPValueEncoding = str
SNMPTable = List[List[DecodedValues]]

SectionName = str
SNMPSectionContent = Union[SNMPTable, List[SNMPTable]]
SNMPSections = Dict[SectionName, SNMPSectionContent]
PersistedSNMPSection = Tuple[int, int, SNMPSectionContent]
PersistedSNMPSections = Dict[SectionName, PersistedSNMPSection]
RawSNMPData = SNMPSections

Column = Union[str, int, Tuple[SNMPValueEncoding, str]]
Columns = List[Column]

OID = str
OIDWithColumns = Tuple[OID, Columns]
OIDWithSubOIDsAndColumns = Tuple[OID, List[OID], Columns]
SingleOIDInfo = Union[OIDWithColumns, OIDWithSubOIDsAndColumns]
MultiOIDInfo = List[SingleOIDInfo]
OIDInfo = Union[SingleOIDInfo, MultiOIDInfo]

RawValue = bytes
SNMPRowInfo = List[Tuple[OID, RawValue]]

# TODO: Be more specific about the possible tuples
# if the credentials are a string, we use that as community,
# if it is a four-tuple, we use it as V3 auth parameters:
# (1) security level (-l)
# (2) auth protocol (-a, e.g. 'md5')
# (3) security name (-u)
# (4) auth password (-A)
# And if it is a six-tuple, it has the following additional arguments:
# (5) privacy protocol (DES|AES) (-x)
# (6) privacy protocol pass phrase (-X)
SNMPCommunity = str
# TODO: This does not work as intended
#SNMPv3NoAuthNoPriv = Tuple[str, str]
#SNMPv3AuthNoPriv = Tuple[str, str, str, str]
#SNMPv3AuthPriv = Tuple[str, str, str, str, str, str]
#SNMPCredentials = Union[SNMPCommunity, SNMPv3NoAuthNoPriv, SNMPv3AuthNoPriv, SNMPv3AuthPriv]
SNMPCredentials = Union[SNMPCommunity, Tuple[str, ...]]

# TODO: Cleanup to named tuple
SNMPTiming = Dict


# Wraps the configuration of a host into a single object for the SNMP code
class SNMPHostConfig(
        NamedTuple("SNMPHostConfig", [
            ("is_ipv6_primary", bool),
            ("hostname", HostName),
            ("ipaddress", HostAddress),
            ("credentials", SNMPCredentials),
            ("port", int),
            ("is_bulkwalk_host", bool),
            ("is_snmpv2or3_without_bulkwalk_host", bool),
            ("bulk_walk_size_of", int),
            ("timing", SNMPTiming),
            ("oid_range_limits", list),
            ("snmpv3_contexts", list),
            ("character_encoding", Optional[str]),
            ("is_usewalk_host", bool),
            ("is_inline_snmp_host", bool),
        ])):
    @property
    def is_snmpv3_host(self):
        # type: () -> bool
        return isinstance(self.credentials, tuple)


# TODO: We should really parse our configuration file and use a
# class/NamedTuple, see above.
def timeperiod_spec_alias(timeperiod_spec, default=u""):
    # type: (TimeperiodSpec, Text) -> Text
    alias = timeperiod_spec.get("alias", default)
    if isinstance(alias, Text):
        return alias
    raise Exception("invalid timeperiod alias %r" % (alias,))
