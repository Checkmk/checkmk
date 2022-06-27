#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#  SYSOID Mapping
#  SYSOID                   MODEL    OS VERSION
#  1.3.6.1.4.1.14685.1.3    XI50     3.8.2.2, 4.0.2.7
#  1.3.6.1.4.1.14685.1.3    XI52     6.0.1.0
#  1.3.6.1.4.1.14685.1.7    XG45     6.0.1.0
#  1.3.6.1.4.1.14685.1.8    Gateway  7.2.0.2


# already migrated!
def scan_datapower(oid):
    return oid(".1.3.6.1.2.1.1.2.0") in [
        ".1.3.6.1.4.1.14685.1.8",
        ".1.3.6.1.4.1.14685.1.7",
        ".1.3.6.1.4.1.14685.1.3",
    ]
