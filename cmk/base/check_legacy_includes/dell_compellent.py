#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file


def dell_compellent_dev_state_map(orig_dev_state):
    return {
        "1": (0, "UP"),
        "2": (2, "DOWN"),
        "3": (1, "DEGRADED"),
    }.get(orig_dev_state, (3, 'unknown[%s]' % orig_dev_state))


def inventory_dell_compellent(info):
    for line in info:
        yield (line[0], None)
