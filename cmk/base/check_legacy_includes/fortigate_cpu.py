#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# tyxpe: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from .cpu_util import check_cpu_util


def inventory_fortigate_cpu(info, default_levels):
    return [(None, default_levels)]


def check_fortigate_cpu(item, params, info):
    num_cpus = 0
    util = 0
    for line in info:
        util += int(line[0])
        num_cpus += 1
    if num_cpus == 0:
        return None

    util = float(util) / num_cpus  # type: ignore[assignment]

    state, infotext, perfdata = next(check_cpu_util(util, params))
    infotext += " at %d CPUs" % num_cpus

    return state, infotext, perfdata
