#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, field
from typing import Dict, Generic, Literal, Mapping, Tuple, TypeVar

VsResult = Mapping[Literal["levels", "levels_lower"], Tuple[float, float]]


@dataclass
class ClientsPerInterface:
    per_interface: Dict[str, int] = field(default_factory=lambda: {})


@dataclass
class ClientsTotal:
    total: int


T = TypeVar("T", ClientsPerInterface, ClientsTotal)


@dataclass
class WlcClientsSection(Generic[T]):
    total_clients: int = 0
    clients_per_ssid: Dict[str, T] = field(default_factory=dict)
