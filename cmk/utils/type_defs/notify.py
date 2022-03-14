#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Optional, Tuple, Union

from ._misc import EventRule

ContactName = str

NotifyPluginParamsList = List[str]
NotifyPluginParamsDict = Dict[str, Any]  # TODO: Improve this
NotifyPluginParams = Union[NotifyPluginParamsList, NotifyPluginParamsDict]
NotifyBulkParameters = Dict[str, Any]  # TODO: Improve this
NotifyRuleInfo = Tuple[str, EventRule, str]
NotifyPluginName = str
NotifyPluginInfo = Tuple[
    ContactName, NotifyPluginName, NotifyPluginParams, Optional[NotifyBulkParameters]
]
NotifyAnalysisInfo = Tuple[List[NotifyRuleInfo], List[NotifyPluginInfo]]

UUIDs = List[Tuple[float, str]]
NotifyBulk = Tuple[str, float, Union[None, str, int], Union[None, str, int], int, UUIDs]
NotifyBulks = List[NotifyBulk]
