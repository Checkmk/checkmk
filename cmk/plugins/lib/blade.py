#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import any_of, contains, equals

DETECT_BLADE = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "BladeCenter Management Module"),
    contains(".1.3.6.1.2.1.1.1.0", "BladeCenter Advanced Management Module"),
    contains(".1.3.6.1.2.1.1.1.0", "IBM Flex Chassis Management Module"),
    contains(".1.3.6.1.2.1.1.1.0", "Lenovo Flex Chassis Management Module"),
)

DETECT_BLADE_BX = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "BX600"),
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.7244.1.1.1"),
)
