#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from typing import Literal, Protocol, TypedDict

from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName


class RRDInterface(Protocol):
    OperationalError: type[Exception]

    def update(self, *args: str) -> None: ...
    def create(self, *args: str) -> None: ...
    def info(self, *args: str) -> Mapping[str, int]: ...


class RRDObjectConfig(TypedDict):
    """RRDObjectConfig
    This typing might not be complete or even wrong, feel free to improve"""

    cfs: Iterable[Literal["MIN", "MAX", "AVERAGE"]]  # conceptually a Set[Literal[...]]
    rras: list[tuple[float, int, int]]
    step: int
    format: Literal["pnp_multiple", "cmc_single"]


class RRDConfig(Protocol):
    def rrd_config(self, hostname: HostName) -> RRDObjectConfig | None: ...

    def rrd_config_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> RRDObjectConfig | None: ...

    def cmc_log_rrdcreation(self) -> Literal["terse", "full"] | None: ...
