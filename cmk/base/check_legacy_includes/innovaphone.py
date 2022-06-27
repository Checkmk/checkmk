#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def check_innovaphone(params, info, unit="%", msg=False):
    warn, crit = params
    current = int(info[0][1])
    message = "Current: %d%s" % (current, unit)
    if msg:
        message += " " + msg
    perf = [("usage", current, warn, crit, 0, 100)]
    if current >= crit:
        return 2, message, perf
    if current >= warn:
        return 1, message, perf
    return 0, message, perf
