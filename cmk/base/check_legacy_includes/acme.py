#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
