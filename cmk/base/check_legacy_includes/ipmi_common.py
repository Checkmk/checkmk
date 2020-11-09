#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=no-else-break

# pylint: disable=consider-using-in

# pylint: disable=no-else-return

from cmk.base.check_api import check_levels
# ==================================================================================================
# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/ipmi.py
# ==================================================================================================
# ==================================================================================================

import cmk.base.plugins.agent_based.utils.ipmi as ipmi

#TODO Cleanup the whole status text mapping in
# ipmi_common.include, ipmi_sensors.include, ipmi


def ipmi_ignore_entry(name, status_txt, rules):
    return True if status_txt is None else ipmi.ignore_sensor(name, status_txt, rules)


def check_ipmi_common(item, params, parsed, what, status_txt_mapping):
    if params is None:
        params = {}

    if item == "Summary" or item == "Summary FreeIPMI":
        return check_ipmi_common_summarized(params, parsed, status_txt_mapping)
    elif item in parsed:
        return check_ipmi_common_detailed(item, params, parsed[item], what, status_txt_mapping)


def ipmi_common_check_levels(sensorname, val, params, unit=""):
    for this_sensorname, levels in params.get("numerical_sensor_levels", []):
        if this_sensorname == sensorname and levels:
            levels_tuple = levels.get('upper', (None, None)) + levels.get('lower', (None, None))
            yield check_levels(val, None, levels_tuple, unit=unit, infoname=sensorname)
            break


def check_ipmi_common_detailed(item, params, data, what, status_txt_mapping):
    val = data["value"]
    unit = data["unit"] or ""
    status_txt = data["status_txt"]
    crit_low = data["crit_low"]
    warn_low = data["warn_low"]
    warn_high = data["warn_high"]
    crit_high = data["crit_high"]

    # stay compatible with older versions
    yield status_txt_mapping(status_txt), "Status: %s" % status_txt

    perfdata = []
    if val is not None:
        if what == "ipmitool":
            old_perf_val = str(val) + unit
            perfdata = [(item, old_perf_val, warn_high, crit_high)]

        elif what == "freeipmi" and \
             ("temperature" in item.lower() or "temp" in item.lower() or unit == 'C'):
            # Do not save performance data for FANs. This produces
            # much data and is - in my opinion - useless.
            perfdata = [("value", val, None, crit_high)]

        status, infotext, _ = check_levels(val, None, (warn_high, crit_high, warn_low, crit_low),
                                           unit)
        yield status, infotext, perfdata
        yield from ipmi_common_check_levels(item, val, params, unit)

    for wato_status_txt, wato_status in params.get("sensor_states", []):
        if status_txt.startswith(wato_status_txt):
            yield wato_status, ""
            break

    # Sensor reports 'nc' ('non critical'), so we set the state to WARNING
    if status_txt.startswith('nc'):
        yield 1, ""


def check_ipmi_common_summarized(params, parsed, status_txt_mapping):
    states = [0]
    warn_texts = []
    crit_texts = []
    ok_texts = []
    skipped_texts = []
    ambient_count = 0
    ambient_sum = 0.0

    for sensorname, data in parsed.items():
        val = data["value"]
        unit = data["unit"]
        status_txt = data["status_txt"]

        # Skip datasets which have no valid data (zero value, no unit and state nc)
        if ipmi_ignore_entry(sensorname, status_txt, params) or \
           (val == '0.000' and unit is None and status_txt.startswith('nc')):
            skipped_texts.append("%s (%s)" % (sensorname, status_txt))
            continue

        sensorstate = status_txt_mapping(status_txt)
        for wato_status_txt, wato_status in params.get("sensor_states", []):
            if status_txt.startswith(wato_status_txt):
                sensorstate = wato_status
                break

        ls, infotext, _ = ipmi_common_check_levels(sensorname, val, params)
        sensorstate = max(sensorstate, ls)

        if sensorstate == 1:
            warn_texts.append(infotext)
        elif sensorstate == 2:
            crit_texts.append(infotext)
        else:
            ok_texts.append(infotext)

        states.append(sensorstate)

        if "amb" in sensorname or "Ambient" in sensorname:
            try:
                ambient_count += 1
                ambient_sum += float(val)
            except (TypeError, ValueError):
                pass

    if ambient_count > 0:
        perfdata = [("ambient_temp", ambient_sum / ambient_count)]  # fixed: true-division
    else:
        perfdata = []

    infotexts = ["%d sensors" % len(parsed)]
    for title, texts, extrainfo, text_state in [("OK", ok_texts, "", 0),
                                                ("WARN", warn_texts, "(!)", 1),
                                                ("CRIT", crit_texts, "(!!)", 2),
                                                ("skipped", skipped_texts, "", 0)]:
        if len(parsed) == len(texts):
            # Everything OK
            infotext = "%d sensors %s" % (len(parsed), title)
            if extrainfo:
                infotext += ": %s%s" % (", ".join(texts), extrainfo)
            infotexts = [infotext]
            break

        elif texts:
            infotext = "%d %s" % (len(texts), title)
            if extrainfo:
                infotext += ": %s%s" % (", ".join(texts), extrainfo)
            infotexts.append(infotext)

            if text_state:
                states.append(text_state)

    return max(states), ' - '.join(infotexts), perfdata
