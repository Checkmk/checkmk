#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

acme_environment_states = {
    "1": (0, "initial"),
    "2": (0, "normal"),
    "3": (1, "minor"),
    "4": (1, "major"),
    "5": (2, "critical"),
    "6": (2, "shutdown"),
    "7": (2, "not present"),
    "8": (2, "not functioning"),
    "9": (2, "unknown"),
}


def scan_acme(oid):
    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.9148")
