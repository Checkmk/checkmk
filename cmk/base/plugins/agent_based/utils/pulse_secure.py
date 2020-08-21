#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..agent_based_api.v0 import contains


def scan_pulse_secure(oid):
    return ".1.3.6.1.4.1.12532" in oid(".1.3.6.1.2.1.1.2.0")


DETECT_PULSE_SECURE = contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12532")


def parse_pulse_secure(info, *keys):

    parsed = {}

    for i, key in enumerate(keys):
        try:
            parsed[key] = int(info[0][i])
        except ValueError:
            pass

    return parsed
