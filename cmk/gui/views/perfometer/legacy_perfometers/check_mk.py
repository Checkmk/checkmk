#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.utils as utils
from cmk.gui.type_defs import Perfdata, Row
from cmk.gui.view_utils import get_themed_perfometer_bg_color

from .utils import (
    LegacyPerfometerResult,
    perfometer_linear,
    perfometer_logarithmic,
    perfometer_logarithmic_dual,
    perfometers,
    render_perfometer,
)


def register() -> None:
    perfometers["check_mk-nfsiostat"] = perfometer_nfsiostat


# Perf-O-Meters for Checkmk's checks
#
# They are called with:
# 1. row -> a dictionary of the data row with at least the
#    keys "service_perf_data", "service_state" and "service_check_command"
# 2. The check command (might be extracted from the performance data
#    in a PNP-like manner, e.g if perfdata is "value=10.5;0;100.0;20;30 [check_disk]
# 3. The parsed performance data as a list of 7-tuples of
#    (varname, value, unit, warn, crit, min, max)


# TODO: Migrate to cmk.utils.render.*
def number_human_readable(n: float, precision: int = 1, unit: str = "B") -> str:
    base = 1024.0
    if unit == "Bit":
        base = 1000.0

    n = float(n)
    f = "%." + str(precision) + "f"
    if abs(n) > base * base * base:
        return (f + "G%s") % (n / (base * base * base), unit)  # fixed: true-division
    if abs(n) > base * base:
        return (f + "M%s") % (n / (base * base), unit)  # fixed: true-division
    if abs(n) > base:
        return (f + "k%s") % (n / base, unit)  # fixed: true-division
    return (f + "%s") % (n, unit)


def perfometer_blower(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    rpm = int(perf_data[0].value)
    return "%d RPM" % rpm, perfometer_logarithmic(rpm, 2000, 1.5, "#88c")


def perfometer_lcp_regulator(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = int(perf_data[0].value)
    return "%d%%" % value, perfometer_linear(value, "#8c8")


def perfometer_bandwidth(in_traffic, out_traffic, in_bw, out_bw, unit="B"):
    traffic_multiplier = 1 if (unit == "B") else 8

    # if we do not have bandwith make logarithmic perf-o-meter
    if in_bw <= 0.0 or out_bw <= 0.0:
        MB = 1000000.0
        readable_in = number_human_readable(in_traffic * traffic_multiplier, 1, unit)
        readable_out = number_human_readable(out_traffic * traffic_multiplier, 1, unit)
        text = f"{readable_in}/s&nbsp;&nbsp;&nbsp;{readable_out}/s"
        return text, perfometer_logarithmic_dual(in_traffic, "#0e6", out_traffic, "#2af", MB, 5)
    # if we have bandwidth
    txt, data = [], []
    for name, bytes_, bw, color in [
        ("in", in_traffic, in_bw, "#0e6"),
        ("out", out_traffic, out_bw, "#2af"),
    ]:
        rrate = bytes_ / bw  # fixed: true-division
        drate = max(0.02, rrate**0.5**0.5)
        rperc = 100 * rrate
        dperc = 100 * drate
        a = (dperc / 2.0, color)
        b = (50 - dperc / 2.0, get_themed_perfometer_bg_color())

        txt.append("%.1f%%" % rperc)
        if name == "in":
            data.extend([b, a])  # white left, color right
        else:
            data.extend([a, b])  # color right, white left
    return " &nbsp; ".join(txt), render_perfometer(data)


# Aiflow in l/s
def perfometer_airflow_ls(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = int(float(perf_data[0].value) * 100)
    return "%sl/s" % perf_data[0].value, perfometer_logarithmic(value, 1000, 2, "#3366cc")


def perfometer_el_inphase(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    for data in perf_data:
        if data.metric_name == "power":
            power = utils.savefloat(data.value)
    return "%.0f W" % power, perfometer_linear(power, "#8050ff")


def perfometer_nfsiostat(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    for pd in perf_data:
        if pd.metric_name == "op_s":
            ops = float(pd.value)
            color = "#ff6347"
            return "%d op/s" % ops, perfometer_linear(ops, color)
    return None
