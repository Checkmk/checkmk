#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

pdu_gude_default_levels = {
    "V": (220, 210),  # Volt
    "A": (15, 16),  # Ampere
    "W": (3500, 3600),  # Watt
}


def inventory_pdu_gude(section):
    yield from (
        (
            pdu_num,
            "pdu_gude_default_levels",
        )
        for pdu_num in section
    )


def check_pdu_gude(item, params, section):
    if not (pdu_properties := section.get(item)):
        return

    for pdu_property in pdu_properties:
        infotext = "%.2f %s" % (
            pdu_property.value,
            pdu_property.unit,
        )

        warn, crit = params.get(pdu_property.unit, (None, None))
        perfdata = [(pdu_property.unit, pdu_property.value, warn, crit)]
        status = 0

        if warn is not None and warn > crit:
            if pdu_property.value < crit:
                status = 2
            elif pdu_property.value < warn:
                status = 1

        else:
            if crit is not None and pdu_property.value > crit:
                status = 2
            elif warn is not None and pdu_property.value > warn:
                status = 1

        yield status, infotext, perfdata
