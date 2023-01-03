#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial

from cmk.utils.type_defs import AgentRawData, result

from cmk.snmplib.type_defs import SNMPRawData, SNMPRawDataSection

from ._parser import Parser
from .host_sections import HostSections
from .type_defs import AgentRawDataSection, SectionNameCollection

__all__ = ["parse_raw_data"]


def parse_raw_data(
    parser: Parser,
    raw_data: result.Result[AgentRawData | SNMPRawData, Exception],
    *,
    selection: SectionNameCollection,
) -> result.Result[HostSections[AgentRawDataSection | SNMPRawDataSection], Exception]:
    try:
        return raw_data.map(partial(parser.parse, selection=selection))
    except Exception as exc:
        return result.Error(exc)
