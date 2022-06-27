#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import check_levels


def check_fan(rpm, params):
    if isinstance(params, tuple):
        params = {"lower": params}

    levels = params.get("upper", (None, None)) + params["lower"]
    return check_levels(
        rpm,
        "fan" if params.get("output_metrics") else None,
        levels,
        unit="RPM",
        human_readable_func=int,
        infoname="Speed",
    )
