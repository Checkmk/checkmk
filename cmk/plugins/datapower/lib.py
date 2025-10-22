#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#  SYSOID Mapping
#  SYSOID                   MODEL    OS VERSION
#  1.3.6.1.4.1.14685.1.3    XI50     3.8.2.2, 4.0.2.7
#  1.3.6.1.4.1.14685.1.3    XI52     6.0.1.0
#  1.3.6.1.4.1.14685.1.7    XG45     6.0.1.0
#  1.3.6.1.4.1.14685.1.8    Gateway  7.2.0.2

from cmk.agent_based.v2 import any_of, equals

DETECT = any_of(
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14685.1.8"),
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14685.1.7"),
    equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14685.1.3"),
)
