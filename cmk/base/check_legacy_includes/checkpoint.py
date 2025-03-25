#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

SENSOR_STATUS_TO_CMK_STATUS: Mapping[str, tuple[Literal[0, 2, 3], str]] = {
    "0": (0, "sensor in range"),
    "1": (2, "sensor out of range"),
    "2": (3, "reading error"),
}
