#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def license_check_levels(total, in_use, params):
    if params is False:
        warn = None
        crit = None
    elif not params:
        warn = total
        crit = total
    elif isinstance(params[0], int):
        warn = max(0, total - params[0])
        crit = max(0, total - params[1])
    else:
        warn = total * (1 - params[0] / 100.0)
        crit = total * (1 - params[1] / 100.0)

    perfdata = [("licenses", in_use, warn, crit, 0, total)]
    if in_use <= total:
        infotext = "used %d out of %d licenses" % (in_use, total)
    else:
        infotext = "used %d licenses, but you have only %d" % (in_use, total)

    if crit is not None and in_use >= crit:
        status = 2
    elif warn is not None and in_use >= warn:
        status = 1
    else:
        status = 0

    if status:
        infotext += " (warn/crit at %d/%d)" % (warn, crit)  # type: ignore[str-format]

    return status, infotext, perfdata
