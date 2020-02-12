#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Checkmk wide type definitions"""

from typing import NewType, Any, Text, Optional, Dict, Set, List

HostName = str
HostAddress = str
HostgroupName = str
ServiceName = Text
ServicegroupName = str
ContactgroupName = str
TimeperiodName = str
RulesetName = str
RuleValue = Any  # TODO: Improve this type
Ruleset = List[Dict]  # TODO: Improve this type
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
CheckVariables = Dict[str, Any]

UserId = NewType("UserId", Text)
EventRule = Dict[str, Any]  # TODO Improve this
