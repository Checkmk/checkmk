#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Type defs intended for Exposure in API
"""
from typing import Any, Callable, Generator, List, Union

from cmk.base.discovered_labels import HostLabel

AgentStringTable = List[List[str]]
AgentParseFunction = Callable[[AgentStringTable], Any]

HostLabelFunction = Callable[[Any], Generator[HostLabel, None, None]]

SNMPStringTable = List[List[List[str]]]
SNMPStringByteTable = List[List[List[Union[str, List[int]]]]]
SNMPParseFunction = Union[Callable[[SNMPStringTable], Any], Callable[[SNMPStringByteTable], Any],]
