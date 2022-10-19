#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils.threepar import parse_3par


@dataclass
class ThreeParHost:
    name: str
    id: int | str
    os: str | None
    fc_paths_number: int
    iscsi_paths_number: int


ThreeParHostsSection = Mapping[str, ThreeParHost]


def parse_threepar_hosts(string_table: StringTable) -> ThreeParHostsSection:

    return {
        host.get("name"): ThreeParHost(
            name=host.get("name"),
            id=host.get("id"),
            os=host.get("descriptors", {}).get("os"),
            fc_paths_number=len(host.get("FCPaths", [])),
            iscsi_paths_number=len(host.get("iSCSIPaths", [])),
        )
        for host in parse_3par(string_table).get("members", {})
        if host.get("name") is not None
    }


register.agent_section(
    name="3par_hosts",
    parse_function=parse_threepar_hosts,
)
