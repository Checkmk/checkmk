#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import division
import math
from typing import List, Optional  # pylint: disable=unused-import

import cmk.utils.debug
from cmk.base.check_utils import RawAgentData  # pylint: disable=unused-import


def our_uptime():
    # type: () -> float
    return float((open("/proc/uptime").read().split()[0]))


# replace simulator tags in output
def process(output):
    # type: (RawAgentData) -> RawAgentData
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
            output = output[:i] + replacement + output[e + 1:]
    except Exception as e:
        if cmk.utils.debug.enabled():
            raise

    return output


def agentsim_uptime(rate=1.0, period=None):  # period = sinus wave
    # type: (float, Optional[float]) -> int
    if period is None:
        return int(our_uptime() * rate)

    a = (rate * period) / (2.0 * math.pi)  # fixed: true-division
    u = our_uptime()
    return int(u * rate + int(a * math.sin(u * 2.0 * math.pi / period)))  # fixed: true-division


def agentsim_enum(values, period=1):  # period is in seconds
    # type: (List[bytes], int) -> bytes
    hit = int(our_uptime() / period % len(values))  # fixed: true-division
    return values[hit]


def agentsim_sinus(base=50, amplitude=50, period=300):
    # type: (int, int, int) -> int
    return int(math.sin(our_uptime() * math.pi * 2.0 / period) * amplitude +
               base)  # fixed: true-division
