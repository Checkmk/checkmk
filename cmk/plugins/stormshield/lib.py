#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import all_of, any_of, equals, exists, startswith

DETECT_STORMSHIELD = all_of(
    any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11256.2.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".10.0.0.1.4.1.11256.1.20.10"),
    ),
    any_of(
        exists(".1.3.6.1.4.1.11256.1.0.1"),
        exists(".1.3.6.1.4.1.11256.1.11.1.0"),
    ),
)

DETECT_STORMSHIELD_CLUSTER = all_of(
    any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.8"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11256.2.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".10.0.0.1.4.1.11256.1.20.10"),
    ),
    any_of(
        exists(".1.3.6.1.4.1.11256.1.0.1"),
        exists(".1.3.6.1.4.1.11256.1.11.1.0"),
    ),
)
