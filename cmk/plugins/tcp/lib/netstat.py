#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import cast

from cmk.agent_based.v2 import check_levels, CheckResult, DiscoveryResult, LevelsT
from cmk.plugins.tcp.lib.models import Connection, Section, SplitIP


def _match_params(connection: Connection, params: Mapping[str, object]) -> bool:
    return all(
        str(params.get(k, v)) == v
        for k, v in [
            ("local_ip", connection.local_address.ip_address),
            ("local_port", connection.local_address.port),
            ("remote_ip", connection.remote_address.ip_address),
            ("remote_port", connection.remote_address.port),
            ("proto", connection.proto),
            ("state", connection.state),
        ]
    )


def check_netstat_generic(
    item: str | None, params: Mapping[str, object], section: Section
) -> CheckResult:
    yield from check_levels(
        value=sum(_match_params(connection, params) for connection in section),
        metric_name="connections",
        levels_upper=cast(LevelsT[int], params["max_states"]),
        levels_lower=cast(LevelsT[int], params["min_states"]),
    )


def discover_netstat_never(section: Section) -> DiscoveryResult:
    yield from ()  # can only be enforced


def split_ip_address(ip_address: str) -> SplitIP:
    parts = ip_address.rsplit(":", 1) if ":" in ip_address else ip_address.rsplit(".", 1)
    return SplitIP(*parts)
