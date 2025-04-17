#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import any_of, startswith

DETECT_NETEXTREME = any_of(
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1916.2"),
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2272.2"),
    # verified for:
    # .1.3.6.1.4.1.2272.202 : VSP-4850GTS
    # .1.3.6.1.4.1.2272.209 : VSP-7254
    # .1.3.6.1.4.1.2272.220 : VSP-8404C
)
