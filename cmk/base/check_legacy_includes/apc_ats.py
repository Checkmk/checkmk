#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
from contextlib import suppress
from typing import NamedTuple, Optional, Sequence


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
    Failure = 1
    OK = 2


class PowerSource(NamedTuple):
    name: str
    status: PowerSupplyStatus


class Status(NamedTuple):
    com_status: Optional[CommunictionStatus]
    selected_source: Optional[Source]
    redundancy: Optional[RedunandancyStatus]
    overcurrent: Optional[OverCurrentStatus]
    powersources: Sequence[PowerSource]

    @classmethod
    def from_raw(cls, line):
        com_state, source, redunancy, overcurrent, *powersources = list(map(_parse_int, line))
        return cls(
            com_status=CommunictionStatus(com_state),
            selected_source=Source(source),
            redundancy=RedunandancyStatus(redunancy),
            overcurrent=OverCurrentStatus(overcurrent),
            powersources=cls.parse_powersources(powersources),
        )

    @staticmethod
    def parse_powersources(raw: list[Optional[int]]) -> Sequence[PowerSource]:
        return [
            PowerSource(name=voltage, status=PowerSupplyStatus(value))
            for voltage, value in zip(["5V", "24V", "3.3V", "1.0V"], raw)
            if value is not None
        ]


def _parse_int(value: str) -> Optional[int]:
    with suppress(ValueError):
        return int(value)
    return None


def is_apc_ats(oid):
    return oid(".1.3.6.1.2.1.1.2.0") in [
        ".1.3.6.1.4.1.318.1.3.11",
        ".1.3.6.1.4.1.318.1.3.32",
        ".1.3.6.1.4.1.318.1.3.38",
    ]
