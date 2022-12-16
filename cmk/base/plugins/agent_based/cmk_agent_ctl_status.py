#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.checkmk import Connection, ControllerSection


def _get_connections_and_validity(connections: Sequence[Mapping[str, Any]]) -> Sequence[Connection]:
    conns = []

    for connection in connections:
        valid_until = datetime.strptime(
            connection["local"]["cert_info"]["to"], "%a, %d %b %Y %H:%M:%S %z"
        )
        valid_for_seconds = valid_until.timestamp() - time.time()
        conns.append(Connection(connection["site_id"], valid_for_seconds))

    return conns


def parse_cmk_agent_ctl_status(string_table: StringTable) -> Optional[ControllerSection]:
    try:
        raw = json.loads(string_table[0][0])
    except IndexError:
        return None

    return ControllerSection(
        # Currently this is all we need. Extend on demand...
        allow_legacy_pull=bool(raw["allow_legacy_pull"]),
        # inoperational sockets only reported since 2.1.0b7
        socket_ready=bool(raw.get("agent_socket_operational", True)),
        ip_allowlist=tuple(str(i) for i in raw["ip_allowlist"]),
        connections=_get_connections_and_validity(raw["connections"]),
    )


register.agent_section(
    name="cmk_agent_ctl_status",
    parse_function=parse_cmk_agent_ctl_status,
)
