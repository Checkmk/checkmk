#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import AgentRawData

from cmk.core_helpers.agent import AgentRawDataSection

from ._abstract import Source

__all__ = ["AgentSource"]


class AgentSource(Source[AgentRawData, AgentRawDataSection]):
    """Configure agent checkers and fetchers."""
