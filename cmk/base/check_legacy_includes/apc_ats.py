#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
from collections.abc import Iterable, Sequence
from contextlib import suppress
from typing import NamedTuple, Self


class CommunictionStatus(enum.Enum):
    NeverDiscovered = 1
    Established = 2
    Lost = 3


class RedunandancyStatus(enum.Enum):
    Lost = 1
    Redundant = 2


class Source(enum.Enum):
    A = 1
    B = 2


class OverCurrentStatus(enum.Enum):
    Exceeded = 1
    OK = 2


class PowerSupplyStatus(enum.Enum):
    # The MIB only defines two valid values "1" and "2". But in reality, the SNMP file may contain
    # a value of "0", too. According to SUP-22815 this case is OK, too.
    NotAvailable = 0
    Failure = 1
    OK = 2


class PowerSource(NamedTuple):
    name: str
    status: PowerSupplyStatus


class Status(NamedTuple):
    com_status: CommunictionStatus | None
    selected_source: Source | None
    redundancy: RedunandancyStatus | None
    overcurrent: OverCurrentStatus | None
    powersources: Sequence[PowerSource]

    @classmethod
    def from_raw(cls, line: Iterable[str]) -> Self:
        com_state, source, redunancy, overcurrent, *powersources = list(map(_parse_int, line))
        return cls(
            com_status=CommunictionStatus(com_state),
            selected_source=Source(source),
            redundancy=RedunandancyStatus(redunancy),
            overcurrent=OverCurrentStatus(overcurrent),
            powersources=cls.parse_powersources(powersources),
        )

    @staticmethod
    def parse_powersources(raw: list[int | None]) -> Sequence[PowerSource]:
        return [
            PowerSource(name=voltage, status=PowerSupplyStatus(value))
            for voltage, value in zip(["5V", "24V", "3.3V", "1.0V"], raw)
            if value is not None
        ]


def _parse_int(value: str) -> int | None:
    with suppress(ValueError):
        return int(value)
    return None
