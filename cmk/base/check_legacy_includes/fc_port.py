#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence


def fc_parse_counter(value: Sequence[int]) -> int:
    # The counters are sent via SNMP as OCTETSTR, which is converted to
    # a byte string by Checkmks SNMP code. The counters seem to be
    # 64 bit big endian values, which are converted to integers here
    if len(value) == 23:
        # recover from "00 00 00 00 00 C0 FE FE"
        value = [int(chr(value[i]) + chr(value[i + 1]), 16) for i in range(0, 24, 3)]
    return sum(b * 256**i for i, b in enumerate(value[::-1]))
