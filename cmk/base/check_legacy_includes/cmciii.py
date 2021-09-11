#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=no-else-return

from cmk.base.plugins.agent_based.utils.temperature import render_temp

from .temperature import check_temperature


def extract_cmciii_lcp_temps(liste):
    miste = []
    for l in liste:
        try:
            miste.append(float(l.split(" ")[0]))
        except ValueError:
            # Dirty hack fix for a dirty check. Ignore all values that can not be
            # converted to floats
            # sh: introduced by lm. But why?
            pass
    return miste


def translate_cmciii_lcp_status(status):
    statusl = status.lower()
    if statusl == "ok":
        return 0
    elif statusl == "warning":
        return 1
    return 3


def inventory_cmciii_lcp_fanunit(zone, direction, info):
    # these checks are considered obsolete as temp_in_out covers the same
    # information
    return []
    # if info:
    #    return [ ("%s LCP Fanunit %s Average" % (zone, direction), {}) ]


def check_cmciii_lcp_fanunit(item, params, info):
    if params is None:
        params = {}
    _unit_desc, unit_status, _desc, status = info[0][1:4]
    temps = extract_cmciii_lcp_temps(info[0][4:])

    status, message, perfdata = check_temperature(
        temps[4],
        params,
        "cmciii_lcp_fanunit_%s" % item,
        dev_status=translate_cmciii_lcp_status(unit_status),
        dev_status_name="Unit: %s" % unit_status,
        dev_levels=(temps[2], temps[3]),
        dev_levels_lower=(temps[1], temps[0]),
    )

    output_unit = params.get("output_unit", "c")

    message += " ; Top/Mid/Bottom: %s/%s/%s" % (
        render_temp(temps[5], output_unit),
        render_temp(temps[6], output_unit),
        render_temp(temps[7], output_unit),
    )

    return status, message, perfdata


def snmp_scan_cmciii_lcp_fanunit(oid):
    return oid(".1.3.6.1.2.1.1.1.0").startswith("Rittal LCP") and oid(
        ".1.3.6.1.4.1.2606.7.4.2.2.1.3.2.6"
    ).startswith("Air.Temperature.DescName")
