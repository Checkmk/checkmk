#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Types and classes used by the API for agent_based plugins
"""
from typing import Any, Callable, Generator, List, NamedTuple

from cmk.base.api import PluginName
from cmk.base.check_utils import AgentSectionContent
from cmk.base.discovered_labels import HostLabel

AgentParseFunction = Callable[[AgentSectionContent], Any]

HostLabelFunction = Callable[[Any], Generator[HostLabel, None, None]]

AgentSectionPlugin = NamedTuple("AgentSectionPlugin", [
    ("name", PluginName),
    ("parsed_section_name", PluginName),
    ("parse_function", AgentParseFunction),
    ("host_label_function", HostLabelFunction),
    ("supercedes", List[PluginName]),
])
