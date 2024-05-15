#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import any_of, startswith

DETECT_QNAP = any_of(
    startswith(".1.3.6.1.2.1.1.1.0", "Linux TS-"), startswith(".1.3.6.1.2.1.1.1.0", "NAS Q")
)
