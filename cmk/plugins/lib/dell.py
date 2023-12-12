#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import all_of, any_of, contains, equals, exists

DETECT_IDRAC_POWEREDGE = equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10892.5")

DETECT_CHASSIS = equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10892.2")

DETECT_OPENMANAGE = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "Open Manage"),
    contains(".1.3.6.1.2.1.1.1.0", "Linux"),
    contains(".1.3.6.1.2.1.1.1.0", "Software: Windows"),
)

DETECT_DELL_COMPELLENT = all_of(
    exists(".1.3.6.1.4.1.674.*"),
    exists(".1.3.6.1.4.1.674.11000.2000.500.1.2.1.0"),
)
