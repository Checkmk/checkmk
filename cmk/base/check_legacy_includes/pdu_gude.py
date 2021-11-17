#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import check_levels

pdu_gude_default_levels = {
    "V": (220, 210),  # Volt
    "A": (15, 16),  # Ampere
    "W": (3500, 3600),  # Watt
}


def inventory_pdu_gude(section):
    yield from ((
        pdu_num,
        "pdu_gude_default_levels",
    ) for pdu_num in section)


def check_pdu_gude(item, params, section):
    if not (pdu_properties := section.get(item)):
        return

    for pdu_property in pdu_properties:
        levels_lower = levels_upper = (None, None)
        warn, crit = params.get(pdu_property.unit, (None, None))
        if warn is not None and warn > crit:
            levels_lower = warn, crit
        else:
            levels_upper = warn, crit

        yield check_levels(
            pdu_property.value,
            pdu_property.unit,
            levels_upper + levels_lower,
            human_readable_func=lambda v: f"{v:.2f} {pdu_property.unit}",  # pylint: disable=cell-var-from-loop
            infoname=pdu_property.label,
        )
