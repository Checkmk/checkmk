#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def parse_db2_dbs(info):
    current_instance = None
    lines = iter(info)
    dbs: dict = {}
    global_timestamp = None
    try:
        while True:
            line = next(lines)
            if line[0].startswith("TIMESTAMP") and not current_instance:
                global_timestamp = int(line[1])
                continue

            if line[0].startswith("[[["):
                current_instance = line[0][3:-3]
                dbs[current_instance] = []
            elif current_instance:
                dbs[current_instance].append(line)
    except Exception:
        pass

    # By returning a tuple, we trick Checkmk
    # Even if no information is available, an empty tuple is something
    # Checkmk won't report any missing agent sections for this type of checks
    return global_timestamp, dbs
