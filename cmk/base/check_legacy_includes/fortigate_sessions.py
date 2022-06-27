#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def fortigate_sessions(sessions, params):
    warn, crit = params
    infotext = "%d Sessions" % sessions
    state = 0
    if sessions >= crit:
        state = 2
    elif sessions >= warn:
        state = 1
    if state:
        infotext += " (warn/crit at %d/%d)" % (warn, crit)
    return state, infotext, [("session", sessions, warn, crit)]
