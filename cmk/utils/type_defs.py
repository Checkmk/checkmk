#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk wide type definitions"""

from typing import Union, NewType, Any, Text, Optional, Dict, Set, List, Tuple

HostName = str
HostAddress = str
HostgroupName = str
ServiceName = Text
ServicegroupName = str
ContactgroupName = str
TimeperiodName = str
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

UserId = NewType("UserId", Text)
EventRule = Dict[str, Any]  # TODO Improve this

AgentHash = NewType("AgentHash", str)
BakeryOpSys = NewType("BakeryOpSys", str)
AgentConfig = Dict[str, Any]  # TODO Split into more sub configs
BakeryHostName = Union[bool, None, HostName]

# TODO: TimeperiodSpec should really be a class or at least a NamedTuple! We
# can easily transform back and forth for serialization.
TimeperiodSpec = Dict[str, Union[Text, List[Tuple[str, str]]]]


# TODO: We should really parse our configuration file and use a
# class/NamedTuple, see above.
def timeperiod_spec_alias(timeperiod_spec, default=u""):
    # type: (TimeperiodSpec, Text) -> Text
    alias = timeperiod_spec.get("alias", default)
    if isinstance(alias, Text):
        return alias
    raise Exception("invalid timeperiod alias %r" % (alias,))
