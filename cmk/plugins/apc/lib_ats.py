#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import any_of, equals, startswith

DETECT = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318")

DETECT_ATS = any_of(
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318.1.3.11"),
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318.1.3.32"),
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318.1.3.38"),
)
