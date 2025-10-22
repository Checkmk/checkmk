#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import all_of, contains, equals, exists, startswith

DETECT_VPLEX = all_of(
    equals(".1.3.6.1.2.1.1.1.0", ""),
    exists(".1.3.6.1.4.1.1139.21.2.2.8.1.*"),
)

DETECT_ISILON = contains(".1.3.6.1.2.1.1.1.0", "isilon")

DETECT_DATADOMAIN = startswith(".1.3.6.1.2.1.1.1.0", "Data Domain OS")
