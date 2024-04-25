#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.render

import cmk.gui.utils as utils
from cmk.gui.type_defs import Perfdata, Row
from cmk.gui.view_utils import get_themed_perfometer_bg_color

from .utils import (
    LegacyPerfometerResult,
    perfometer_linear,
    perfometer_logarithmic,
    perfometer_logarithmic_dual,
    perfometer_logarithmic_dual_independent,
    perfometers,
    render_perfometer,
)


def register() -> None:
    perfometers["check_mk-genu_pfstate"] = perfometer_genu_screen
    perfometers["check_mk-db2_mem"] = perfometer_simple_mem_usage
    perfometers["check_mk-innovaphone_mem"] = perfometer_simple_mem_usage
    perfometers["check_mk-juniper_screenos_mem"] = perfometer_simple_mem_usage
    perfometers["check_mk-netscaler_mem"] = perfometer_simple_mem_usage
    perfometers["check_mk-arris_cmts_mem"] = perfometer_simple_mem_usage
    perfometers["check_mk-juniper_trpz_mem"] = perfometer_simple_mem_usage
    perfometers["check_mk-apc_mod_pdu_modules"] = perfometer_apc_mod_pdu_modules
    perfometers["check_mk-apc_inrow_airflow"] = perfometer_airflow_ls
    perfometers["check_mk-apc_inrow_fanspeed"] = perfometer_fanspeed
    perfometers["check_mk-hitachi_hnas_fan"] = perfometer_fanspeed_logarithmic
    perfometers["check_mk-arcserve_backup"] = perfometer_check_mk_arcserve_backup
    perfometers["check_mk-ibm_svc_host"] = perfometer_check_mk_ibm_svc_host
    perfometers["check_mk-ibm_svc_license"] = perfometer_check_mk_ibm_svc_license
    perfometers["check_mk-innovaphone_licenses"] = perfometer_licenses_percent
    perfometers["check_mk-citrix_licenses"] = perfometer_licenses_percent
    perfometers["check_mk-zfs_arc_cache"] = perfometer_cache_hit_ratio
    perfometers["check_mk-adva_fsp_current"] = perfometer_current
    perfometers["check_mk-raritan_pdu_inlet"] = perfometer_raritan_pdu_inlet
    perfometers["check_mk-raritan_pdu_inlet_summary"] = perfometer_raritan_pdu_inlet
    perfometers["check_mk-raritan_pdu_outletcount"] = perfometer_raritan_pdu_outletcount
    perfometers["check_mk-docsis_channels_downstream"] = perfometer_dbmv
    perfometers["check_mk-docsis_cm_status"] = perfometer_dbmv
    perfometers["check_mk-veeam_client"] = perfometer_veeam_client
    perfometers["check_mk-ups_socomec_outphase"] = perfometer_ups_outphase
    perfometers["check_mk-raritan_pdu_inlet"] = perfometer_el_inphase
    perfometers["check_mk-raritan_pdu_inlet_summary"] = perfometer_el_inphase
    perfometers["check_mk-f5_bigip_vserver"] = perfometer_f5_bigip_vserver
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


def perfometer_genu_screen(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    value = int(perf[0].value)
    return "%d Sessions" % value, perfometer_logarithmic(value, 5000, 2, "#7109AA")


def perfometer_simple_mem_usage(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    entry = perf[0]
    if entry.max is None:
        return None
    used_perc = (100.0 / entry.max) * entry.value
    return "%d%%" % used_perc, perfometer_linear(used_perc, "#20cf80")


def perfometer_apc_mod_pdu_modules(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = int(utils.savefloat(perf_data[0].value) * 100)
    return "%skw" % perf_data[0].value, perfometer_logarithmic(value, 500, 2, "#3366CC")


# Aiflow in l/s
def perfometer_airflow_ls(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = int(float(perf_data[0].value) * 100)
    return "%sl/s" % perf_data[0].value, perfometer_logarithmic(value, 1000, 2, "#3366cc")


def perfometer_fanspeed(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = float(perf_data[0].value)
    return "%.2f%%" % value, perfometer_linear(value, "silver")


def perfometer_fanspeed_logarithmic(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = float(perf_data[0].value)
    return "%d rpm" % value, perfometer_logarithmic(value, 5000, 2, "silver")


def perfometer_check_mk_arcserve_backup(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    bytes_ = int(perf_data[2].value)
    text = number_human_readable(bytes_)

    return text, perfometer_logarithmic(bytes_, 1000 * 1024 * 1024 * 1024, 2, "#BDC6DE")


def perfometer_check_mk_ibm_svc_host(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    if len(perf_data) < 5:
        return None

    active = int(perf_data[0].value)
    inactive = int(perf_data[1].value)
    degraded = int(perf_data[2].value)
    offline = int(perf_data[3].value)
    other = int(perf_data[4].value)
    total = active + inactive + degraded + offline + other
    data = []
    if active > 0:
        perc_active = active * 100.0 / total
        data.append((perc_active, "#008000"))
    if inactive > 0:
        perc_inactive = inactive * 100.0 / total
        data.append((perc_inactive, "#0000FF"))
    if degraded > 0:
        perc_degraded = degraded * 100.0 / total
        data.append((perc_degraded, "#F84"))
    if offline > 0:
        perc_offline = offline * 100.0 / total
        data.append((perc_offline, "#FF0000"))
    if other > 0:
        perc_other = other * 100.0 / total
        data.append((perc_other, "#000000"))
    if total == 0:
        data.append((100, get_themed_perfometer_bg_color()))
    return "%d active" % active, render_perfometer(data)


def perfometer_check_mk_ibm_svc_license(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    if len(perf_data) < 2:
        return None

    licensed = float(perf_data[0].value)
    used = float(perf_data[1].value)
    if used == 0 and licensed == 0:
        return "0 of 0 used", perfometer_linear(100, get_themed_perfometer_bg_color())
    if licensed == 0:
        return "completely unlicensed", perfometer_linear(100, "silver")

    perc_used = used * 100.0 / licensed
    return "%0.2f %% used" % perc_used, perfometer_linear(perc_used, "silver")


def perfometer_licenses_percent(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    licenses = perf_data[0].value
    max_avail = perf_data[0].max
    if max_avail is None:
        return None
    used_perc = 100.0 * licenses / max_avail
    return "%.0f%% used" % used_perc, perfometer_linear(used_perc, "orange")


def perfometer_cache_hit_ratio(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    hit_ratio = float(perf_data[0].value)  # is already percentage
    color = "#60f020"
    return "%.2f %% hits" % hit_ratio, perfometer_linear(hit_ratio, color)


def perfometer_current(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    display_color = "#50f020"

    value = utils.savefloat(perf_data[0].value)
    crit = utils.savefloat(perf_data[0].crit)
    warn = utils.savefloat(perf_data[0].warn)
    current_perc = (
        value / crit * 90
    )  # critical is at 90% to allow for more than crit # fixed: true-division

    if value > warn:
        display_color = "#FDC840"
    if value > crit:
        display_color = "#FF0000"

    display_string = "%.1f Ampere" % value
    return display_string, perfometer_linear(current_perc, display_color)


def perfometer_raritan_pdu_inlet(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    display_color = "#50f020"
    cap = perf_data[0].metric_name.split("-")[-1]
    value = float(perf_data[0].value)
    unit = perf_data[0].unit_name
    display_str = f"{perf_data[0].value} {unit}"
    if cap.startswith("rmsCurrent"):
        return display_str, perfometer_logarithmic(value, 1, 2, display_color)
    if cap.startswith("unbalancedCurrent"):
        return display_str, perfometer_linear(value, display_color)
    if cap.startswith("rmsVoltage"):
        return display_str, perfometer_logarithmic(value, 500, 2, display_color)
    if cap.startswith("activePower"):
        return display_str, perfometer_logarithmic(value, 20, 2, display_color)
    if cap.startswith("apparentPower"):
        return display_str, perfometer_logarithmic(value, 20, 2, display_color)
    if cap.startswith("powerFactor"):
        return display_str, perfometer_linear(value * 100, display_color)
    if cap.startswith("activeEnergy"):
        return display_str, perfometer_logarithmic(value, 100000, 2, display_color)
    if cap.startswith("apparentEnergy"):
        return display_str, perfometer_logarithmic(value, 100000, 2, display_color)
    return "unimplemented", perfometer_linear(0, get_themed_perfometer_bg_color())


def perfometer_raritan_pdu_outletcount(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    outletcount = float(perf_data[0].value)
    return "%d" % outletcount, perfometer_logarithmic(outletcount, 20, 2, "#da6")


def perfometer_dbmv(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    dbmv = float(perf_data[0].value)
    return "%.1f dBmV" % dbmv, perfometer_logarithmic(dbmv, 50, 2, "#da6")


def perfometer_veeam_client(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    for graph in perf_data:
        if graph.metric_name == "avgspeed":
            avgspeed_bytes = int(graph.value)
        if graph.metric_name == "duration":
            duration_secs = int(graph.value)
    h = perfometer_logarithmic_dual_independent(
        avgspeed_bytes, "#54b948", 10000000, 2, duration_secs, "#2098cb", 500, 2
    )

    avgspeed = cmk.utils.render.fmt_bytes(avgspeed_bytes)
    duration = cmk.utils.render.approx_age(duration_secs)

    return f"{avgspeed}/s&nbsp;&nbsp;&nbsp;{duration}", h


def perfometer_ups_outphase(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    load = int(perf_data[2].value)
    return "%d%%" % load, perfometer_linear(load, "#8050ff")


def perfometer_el_inphase(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    for data in perf_data:
        if data.metric_name == "power":
            power = utils.savefloat(data.value)
    return "%.0f W" % power, perfometer_linear(power, "#8050ff")


def perfometer_f5_bigip_vserver(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    connections = int(perf_data[0].value)
    return str(connections), perfometer_logarithmic(connections, 100, 2, "#46a")


def perfometer_nfsiostat(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    for pd in perf_data:
        if pd.metric_name == "op_s":
            ops = float(pd.value)
            color = "#ff6347"
            return "%d op/s" % ops, perfometer_linear(ops, color)
    return None
