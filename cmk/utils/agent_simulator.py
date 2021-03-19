#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from typing import List, Optional

import cmk.utils.debug
from cmk.utils.type_defs import AgentRawData


def our_uptime() -> float:
    return float((open("/proc/uptime").read().split()[0]))


# replace simulator tags in output
def process(output: AgentRawData) -> AgentRawData:
    try:
        while True:
            i = output.find(b'%{')
            if i == -1:
                break
            e = output.find(b'}', i)
            if e == -1:
                break
            simfunc = output[i + 2:e]
            replacement = str(eval(b"agentsim_" + simfunc)).encode("utf-8")  # nosec
            output = AgentRawData(output[:i] + replacement + output[e + 1:])
    except Exception as e:
        if cmk.utils.debug.enabled():
            raise

    return output


def agentsim_uptime(rate: float = 1.0,
                    period: Optional[float] = None) -> int:  # period = sinus wave
    if period is None:
        return int(our_uptime() * rate)

    a = (rate * period) / (2.0 * math.pi)  # fixed: true-division
    u = our_uptime()
    return int(u * rate + int(a * math.sin(u * 2.0 * math.pi / period)))  # fixed: true-division


def agentsim_enum(values: List[bytes], period: int = 1) -> bytes:  # period is in seconds
    hit = int(our_uptime() / period % len(values))  # fixed: true-division
    return values[hit]


def agentsim_sinus(base: int = 50, amplitude: int = 50, period: int = 300) -> int:
    return int(math.sin(our_uptime() * math.pi * 2.0 / period) * amplitude +
               base)  # fixed: true-division
