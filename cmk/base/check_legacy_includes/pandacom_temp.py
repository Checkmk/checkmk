#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .temperature import check_temperature

# suggested by customer
PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS = {"levels": (35, 40)}


def inventory_pandacom_module_temp(info):
    return [(line[0], {}) for line in info]


def check_pandacom_module_temp(item, params, info):
    for slot, temp_str, warn_str, crit_str in info:
        if slot == item:
            return check_temperature(
                int(temp_str),
                params,
                "pandacom_%s" % item,
                dev_levels=(int(warn_str), int(crit_str)),
            )
    return None
