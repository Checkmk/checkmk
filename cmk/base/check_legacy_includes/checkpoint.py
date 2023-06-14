#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


checkpoint_sensorstatus_to_nagios = {
    "0": (0, "sensor in range"),
    "1": (2, "sensor out of range"),
    "2": (3, "reading error"),
}
