#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

VsResult = Mapping[Literal["levels", "levels_lower"], tuple[float, float]]


@dataclass
class ClientsPerInterface:
    per_interface: dict[str, int] = field(default_factory=lambda: {})


@dataclass
class ClientsTotal:
    total: int


@dataclass
class WlcClientsSection[T: (ClientsPerInterface, ClientsTotal)]:
    total_clients: int = 0
    clients_per_ssid: dict[str, T] = field(default_factory=dict)
