#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.render
from cmk.utils.render import SecondsRenderer

import cmk.gui.utils as utils
from cmk.gui.globals import html
from cmk.gui.plugins.views.perfometers.utils import (
    LegacyPerfometerResult,
    Perfdata,
    perfometer_linear,
    perfometer_logarithmic,
    perfometer_logarithmic_dual,
    perfometer_logarithmic_dual_independent,
    perfometers,
    render_perfometer,
    Row,
)
from cmk.gui.utils.html import HTML
from cmk.gui.view_utils import get_themed_perfometer_bg_color

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


def perfometer_check_mk_mem_used(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    ram_used = None
    ram_total = None
    swap_used = None
    swap_total = None

    for entry in perf_data:
        # Get total and used RAM
        if entry[0] == "ramused":
            ram_used = float(entry[1])  # mem.include
            ram_total = entry[6]  # mem.include
        elif entry[0] == "mem_used":
            ram_used = float(entry[1])  # mem.linux
        elif entry[0] == "mem_total":
            ram_total = float(entry[1])  # mem.linux

        # Get total and used SWAP
        elif entry[0] == "swapused":
            swap_used = float(entry[1])  # mem.include
            swap_total = entry[6]  # mem.include
        elif entry[0] == "swap_used":
            swap_used = float(entry[1])  # mem.linux
        elif entry[0] == "swap_total":
            swap_total = float(entry[1])  # mem.linux

    if not ram_used or ram_total is None or swap_used is None or swap_total is None:
        return None

    virt_total = ram_total + swap_total
    virt_used = ram_used + swap_used

    # paint used ram and swap
    ram_color, swap_color = "#80ff40", "#008030"

    data = [
        (ram_used * 100.0 / virt_total, ram_color),
        (swap_used * 100.0 / virt_total, swap_color),
    ]

    # used virtual memory < ram => show free ram and free total virtual memory
    if virt_used < ram_total:
        data.append(
            ((ram_total - virt_used) * 100.0 / virt_total, get_themed_perfometer_bg_color())
        )
        data.append(((virt_total - ram_total) * 100.0 / virt_total, "#ccc"))
    # usage exceeds ram => show only free virtual memory
    else:
        data.append((100 * (virt_total - virt_used), "#ccc"))
    return "%d%%" % (100 * (virt_used / ram_total)), render_perfometer(data)  # fixed: true-division


perfometers["check_mk-mem.used"] = perfometer_check_mk_mem_used
perfometers["check_mk-mem.linux"] = perfometer_check_mk_mem_used
perfometers["check_mk-aix_memory"] = perfometer_check_mk_mem_used
perfometers["check_mk-hr_mem"] = perfometer_check_mk_mem_used


def perfometer_check_mk_mem_win(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    # only show mem usage, do omit page file
    color = "#5090c0"
    ram_total = perf_data[0][6]
    if ram_total is None:
        return None
    ram_used = perf_data[0][1]
    perc = ram_used / ram_total * 100.0  # fixed: true-division
    return "%d%%" % perc, perfometer_linear(perc, color)


perfometers["check_mk-mem.win"] = perfometer_check_mk_mem_win


def perfometer_check_mk_kernel(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    rate = float(perf_data[0][1])
    return "%.1f/s" % rate, perfometer_logarithmic(rate, 1000, 2, "#da6")


perfometers["check_mk-kernel"] = perfometer_check_mk_kernel


def perfometer_check_mk_ntp(row, check_command, perf_data, unit="ms"):
    offset = float(perf_data[0][1])
    absoffset = abs(offset)
    crit = float(perf_data[0][4])
    max_ = crit * 2
    absoffset = min(absoffset, max_)
    rel = 50 * (absoffset / max_)  # fixed: true-division

    color = {0: "#0f8", 1: "#ff2", 2: "#f22", 3: "#fa2"}[row["service_state"]]
    if offset > 0:
        data = [
            (50, get_themed_perfometer_bg_color()),
            (rel, color),
            (50 - rel, get_themed_perfometer_bg_color()),
        ]
    else:
        data = [
            (50 - rel, get_themed_perfometer_bg_color()),
            (rel, color),
            (50, get_themed_perfometer_bg_color()),
        ]
    return "%.2f %s" % (offset, unit), render_perfometer(data)


perfometers["check_mk-ntp"] = perfometer_check_mk_ntp
perfometers["check_mk-ntp.time"] = perfometer_check_mk_ntp
perfometers["check_mk-chrony"] = perfometer_check_mk_ntp
perfometers["check_mk-systemtime"] = lambda r, c, p: perfometer_check_mk_ntp(r, c, p, "s")


def perfometer_ipmi_sensors(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    state = row["service_state"]
    color = "#39f"
    value = float(perf_data[0][1])
    crit = utils.savefloat(perf_data[0][4])
    if not crit:
        return "%d" % int(value), perfometer_logarithmic(value, 40, 1.2, color)

    perc = value * 100.0 / crit
    # some sensors get critical if the value is < crit (fans), some if > crit (temp)
    if value <= crit:
        data = [(perc, color), (100 - perc, get_themed_perfometer_bg_color())]
    elif state == 0:  # fan, OK
        m = max(value, 10000.0)
        perc_crit = crit * 100.0 / m
        perc_value = (value - crit) * 100.0 / m
        perc_free = (m - value) * 100.0 / m
        data = [
            (perc_crit, color),
            (perc_value, color),
            (perc_free, get_themed_perfometer_bg_color()),
        ]
    else:
        data = []

    if perf_data[0][0] == "temp":
        unit = "°C"
    else:
        unit = ""
    return ("%d%s" % (int(value), unit)), render_perfometer(data)


perfometers["check_mk-ipmi_sensors"] = perfometer_ipmi_sensors


def perfometer_temperature(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    color = "#39f"
    value = float(perf_data[0][1])
    return "%d °C" % int(value), perfometer_logarithmic(value, 40, 1.2, color)


perfometers["check_mk-nvidia.temp"] = perfometer_temperature
perfometers["check_mk-cisco_temp_sensor"] = perfometer_temperature
perfometers["check_mk-cisco_temp_perf"] = perfometer_temperature
perfometers["check_mk-cmctc_lcp.temp"] = perfometer_temperature
perfometers["check_mk-cmctc.temp"] = perfometer_temperature
perfometers["check_mk-smart.temp"] = perfometer_temperature
perfometers["check_mk-f5_bigip_chassis_temp"] = perfometer_temperature
perfometers["check_mk-f5_bigip_cpu_temp"] = perfometer_temperature
perfometers["check_mk-hp_proliant_temp"] = perfometer_temperature
perfometers["check_mk-akcp_sensor_temp"] = perfometer_temperature
perfometers["check_mk-akcp_daisy_temp"] = perfometer_temperature
perfometers["check_mk-fsc_temp"] = perfometer_temperature
perfometers["check_mk-viprinet_temp"] = perfometer_temperature
perfometers["check_mk-hwg_temp"] = perfometer_temperature
perfometers["check_mk-sensatronics_temp"] = perfometer_temperature
perfometers["check_mk-apc_inrow_temperature"] = perfometer_temperature
perfometers["check_mk-hitachi_hnas_temp"] = perfometer_temperature
perfometers["check_mk-dell_poweredge_temp"] = perfometer_temperature
perfometers["check_mk-dell_chassis_temp"] = perfometer_temperature
perfometers["check_mk-dell_om_sensors"] = perfometer_temperature
perfometers["check_mk-innovaphone_temp"] = perfometer_temperature
perfometers["check_mk-cmciii.temp"] = perfometer_temperature
perfometers["check_mk-ibm_svc_enclosurestats.temp"] = perfometer_temperature
perfometers["check_mk-wagner_titanus_topsense.temp"] = perfometer_temperature
perfometers["check_mk-enterasys_temp"] = perfometer_temperature
perfometers["check_mk-adva_fsp_temp"] = perfometer_temperature
perfometers["check_mk-allnet_ip_sensoric.temp"] = perfometer_temperature
perfometers["check_mk-qlogic_sanbox.temp"] = perfometer_temperature
perfometers["check_mk-bintec_sensors.temp"] = perfometer_temperature
perfometers["check_mk-knuerr_rms_temp"] = perfometer_temperature
perfometers["check_mk-arris_cmts_temp"] = perfometer_temperature
perfometers["check_mk-casa_cpu_temp"] = perfometer_temperature
perfometers["check_mk-rms200_temp"] = perfometer_temperature
perfometers["check_mk-juniper_screenos_temp"] = perfometer_temperature
perfometers["check_mk-lnx_thermal"] = perfometer_temperature
perfometers["check_mk-climaveneta_temp"] = perfometer_temperature
perfometers["check_mk-carel_sensors"] = perfometer_temperature
perfometers["check_mk-netscaler_health.temp"] = perfometer_temperature
perfometers["check_mk-kentix_temp"] = perfometer_temperature
perfometers["check_mk-ucs_bladecenter_fans.temp"] = perfometer_temperature
perfometers["check_mk-ucs_bladecenter_psu.chassis_temp"] = perfometer_temperature
perfometers["check_mk-cisco_temperature"] = perfometer_temperature


def perfometer_temperature_multi(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    display_value = -1
    display_color = "#60f020"

    for _sensor, value, _uom, warn, crit, _min, _max in perf_data:
        value = int(value)
        if value > display_value:
            display_value = value

            if warn is not None and display_value > int(warn):
                display_color = "#FFC840"
            if crit is not None and display_value > int(crit):
                display_color = "#FF0000"

    display_string = "%s °C" % display_value
    return display_string, perfometer_linear(display_value, display_color)


perfometers["check_mk-brocade_mlx_temp"] = perfometer_temperature_multi


def perfometer_power(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    display_color = "#60f020"

    value = utils.savefloat(perf_data[0][1])
    crit = utils.savefloat(perf_data[0][4])
    warn = utils.savefloat(perf_data[0][3])
    power_perc = (
        value / crit * 90
    )  # critical is at 90% to allow for more than crit # fixed: true-division

    if value > warn:
        display_color = "#FFC840"
    if value > crit:
        display_color = "#FF0000"

    display_string = "%.1f Watt" % value
    return display_string, perfometer_linear(power_perc, display_color)


perfometers["check_mk-dell_poweredge_amperage.power"] = perfometer_power
perfometers["check_mk-dell_chassis_power"] = perfometer_power
perfometers["check_mk-dell_chassis_powersupplies"] = perfometer_power
perfometers["check_mk-hp-proliant_power"] = perfometer_power


def perfometer_power_simple(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    watt = int(perf_data[0][1])
    text = "%s Watt" % watt
    return text, perfometer_logarithmic(watt, 150, 2, "#60f020")


perfometers["check_mk-ibm_svc_enclosurestats.power"] = perfometer_power_simple
perfometers["check_mk-sentry_pdu"] = perfometer_power_simple


def perfometer_users(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    color = "#39f"
    value = float(perf_data[0][1])
    return "%d users" % int(value), perfometer_logarithmic(value, 50, 2, color)


perfometers["check_mk-hitachi_hnas_cifs"] = perfometer_users


def perfometer_blower(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    rpm = int(perf_data[0][1])
    return "%d RPM" % rpm, perfometer_logarithmic(rpm, 2000, 1.5, "#88c")


perfometers["check_mk-cmctc_lcp.blower"] = perfometer_blower


def perfometer_lcp_regulator(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = int(perf_data[0][1])
    return "%d%%" % value, perfometer_linear(value, "#8c8")


perfometers["check_mk-cmctc_lcp.regulator"] = perfometer_lcp_regulator


def perfometer_bandwidth(in_traffic, out_traffic, in_bw, out_bw, unit="B"):
    traffic_multiplier = 1 if (unit == "B") else 8

    # if we do not have bandwith make logarithmic perf-o-meter
    if in_bw <= 0.0 or out_bw <= 0.0:
        MB = 1000000.0
        readable_in = number_human_readable(in_traffic * traffic_multiplier, 1, unit)
        readable_out = number_human_readable(out_traffic * traffic_multiplier, 1, unit)
        text = "%s/s&nbsp;&nbsp;&nbsp;%s/s" % (readable_in, readable_out)
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


def perfometer_check_mk_if(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    unit = "Bit" if "Bit/s" in row["service_plugin_output"] else "B"
    return perfometer_bandwidth(
        in_traffic=utils.savefloat(perf_data[0][1]),
        out_traffic=utils.savefloat(perf_data[5][1]),
        in_bw=utils.savefloat(perf_data[0][6]),
        out_bw=utils.savefloat(perf_data[5][6]),
        unit=unit,
    )


perfometers["check_mk-if"] = perfometer_check_mk_if
perfometers["check_mk-if64"] = perfometer_check_mk_if
perfometers["check_mk-if64_tplink"] = perfometer_check_mk_if
perfometers["check_mk-winperf_if"] = perfometer_check_mk_if
perfometers["check_mk-vms_if"] = perfometer_check_mk_if
perfometers["check_mk-if_lancom"] = perfometer_check_mk_if
perfometers["check_mk-lnx_if"] = perfometer_check_mk_if
perfometers["check_mk-hpux_if"] = perfometer_check_mk_if
perfometers["check_mk-mcdata_fcport"] = perfometer_check_mk_if
perfometers["check_mk-esx_vsphere_counters.if"] = perfometer_check_mk_if
perfometers["check_mk-hitachi_hnas_fc_if"] = perfometer_check_mk_if
perfometers["check_mk-statgrab_net"] = perfometer_check_mk_if
perfometers["check_mk-netapp_api_if"] = perfometer_check_mk_if
perfometers["check_mk-if_brocade"] = perfometer_check_mk_if
perfometers["check_mk-ucs_bladecenter_if"] = perfometer_check_mk_if
perfometers["check_mk-aix_if"] = perfometer_check_mk_if
perfometers["check_mk-if_fortigate"] = perfometer_check_mk_if


def perfometer_check_mk_fc_port(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    unit = "B"
    return perfometer_bandwidth(
        in_traffic=utils.savefloat(perf_data[0][1]),
        out_traffic=utils.savefloat(perf_data[1][1]),
        in_bw=utils.savefloat(perf_data[0][6]),
        out_bw=utils.savefloat(perf_data[1][6]),
        unit=unit,
    )


perfometers["check_mk-fc_port"] = perfometer_check_mk_fc_port


def perfometer_check_mk_brocade_fcport(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    return perfometer_bandwidth(
        in_traffic=utils.savefloat(perf_data[0][1]),
        out_traffic=utils.savefloat(perf_data[1][1]),
        in_bw=utils.savefloat(perf_data[0][6]),
        out_bw=utils.savefloat(perf_data[1][6]),
    )


perfometers["check_mk-brocade_fcport"] = perfometer_check_mk_brocade_fcport
perfometers["check_mk-qlogic_fcport"] = perfometer_check_mk_brocade_fcport


def perfometer_check_mk_cisco_qos(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    unit = "Bit" if "Bit/s" in row["service_plugin_output"] else "B"
    return perfometer_bandwidth(
        in_traffic=utils.savefloat(perf_data[0][1]),
        out_traffic=utils.savefloat(perf_data[1][1]),
        in_bw=utils.savefloat(perf_data[0][5]),
        out_bw=utils.savefloat(perf_data[1][5]),
        unit=unit,
    )


perfometers["check_mk-cisco_qos"] = perfometer_check_mk_cisco_qos


def perfometer_oracle_tablespaces(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    current = float(perf_data[0][1])
    used = float(perf_data[1][1])
    max_ = float(perf_data[2][1])
    used_perc = used / max_ * 100  # fixed: true-division
    curr_perc = (current / max_ * 100) - used_perc  # fixed: true-division
    data = [
        (used_perc, "#f0b000"),
        (curr_perc, "#00ff80"),
        (100 - used_perc - curr_perc, "#80c0ff"),
    ]
    return "%.1f%%" % used_perc, render_perfometer(data)


perfometers["check_mk-oracle_tablespaces"] = perfometer_oracle_tablespaces


def perfometer_check_oracle_dataguard_stats(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    perfdata_found = False
    perfdata1 = 0.0

    for data in perf_data:
        if data[0] == "apply_lag":
            color = "#80F000"

            perfdata_found = True

            days, hours, minutes, _seconds = SecondsRenderer.get_tuple(int(data[1]))
            perfdata1 = data[1]

    if not perfdata_found:
        days = 0
        hours = 0
        minutes = 0
        color = "#008f48"

    return "%02dd %02dh %02dm" % (days, hours, minutes), perfometer_logarithmic(
        perfdata1, 2592000, 2, color
    )


perfometers["check_mk-oracle_dataguard_stats"] = perfometer_check_oracle_dataguard_stats


def perfometer_oracle_sessions(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    if check_command != "check_mk-oracle_sessions":
        color = "#008f48"
        unit = ""
    else:
        color = "#4800ff"
        unit = "/h"
    value = int(perf_data[0][1])
    return "%d%s" % (value, unit), perfometer_logarithmic(value, 50, 2, color)


perfometers["check_mk-oracle_sessions"] = perfometer_oracle_sessions
perfometers["check_mk-oracle_logswitches"] = perfometer_oracle_sessions
perfometers["check_mk-oracle_processes"] = perfometer_oracle_sessions


def perfometer_cpu_utilization(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    util = float(perf_data[0][1])  # is already percentage
    color = "#60c080"
    return "%.0f %%" % util, perfometer_linear(util, color)


# perfometer_linear(perc, color)
perfometers["check_mk-h3c_lanswitch_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-winperf_processor.util"] = perfometer_cpu_utilization
perfometers["check_mk-netapp_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-cisco_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-juniper_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-brocade_mlx.module_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-hitachi_hnas_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-hitachi_hnas_fpga"] = perfometer_cpu_utilization
perfometers["check_mk-hr_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-innovaphone_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-enterasys_cpu_util"] = perfometer_cpu_utilization
perfometers["check_mk-juniper_trpz_cpu_util"] = perfometer_cpu_utilization
perfometers["check_mk-ibm_svc_nodestats.cpu_util"] = perfometer_cpu_utilization
perfometers["check_mk-ibm_svc_systemstats.cpu_util"] = perfometer_cpu_utilization
perfometers["check_mk-sni_octopuse_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-casa_cpu_util"] = perfometer_cpu_utilization
perfometers["check_mk-juniper_screenos_cpu"] = perfometer_cpu_utilization


def perfometer_ps(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    perf_dict = {p[0]: float(p[1]) for p in perf_data}
    try:
        perc = perf_dict["pcpu"]
        return "%.1f%%" % perc, perfometer_linear(perc, "#30ff80")
    except Exception:
        return None


perfometers["check_mk-ps"] = perfometer_ps


def perfometer_hpux_snmp_cs_cpu(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    data = [
        (float(perf_data[0][1]), "#60f020"),
        (float(perf_data[1][1]), "#ff6000"),
        (float(perf_data[2][1]), "#00d080"),
        (float(perf_data[3][1]), get_themed_perfometer_bg_color()),
    ]
    total = float(perf_data[0][1]) + float(perf_data[1][1]) + float(perf_data[2][1])
    return "%.0f%%" % total, render_perfometer(data)


perfometers["check_mk-hpux_snmp_cs.cpu"] = perfometer_hpux_snmp_cs_cpu


def perfometer_check_mk_uptime(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    seconds = int(float(perf_data[0][1]))
    days, rest = divmod(seconds, 60 * 60 * 24)
    hours, rest = divmod(rest, 60 * 60)
    minutes, seconds = divmod(rest, 60)

    return "%02dd %02dh %02dm" % (days, hours, minutes), perfometer_logarithmic(
        seconds, 2592000.0, 2, "#80F000"
    )


perfometers["check_mk-uptime"] = perfometer_check_mk_uptime
perfometers["check_mk-snmp_uptime"] = perfometer_check_mk_uptime
perfometers["check_mk-esx_vsphere_counters.uptime"] = perfometer_check_mk_uptime
perfometers["check_mk-oracle_instance"] = perfometer_check_mk_uptime


def perfometer_check_mk_diskstat(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    # No Perf-O-Meter for legacy version of diskstat possible
    if len(perf_data) < 2:
        return None

    read_bytes = float(perf_data[0][1])
    write_bytes = float(perf_data[1][1])

    text = "%-.2f M/s  %-.2f M/s" % (
        read_bytes / (1024.0 * 1024.0),
        write_bytes / (1024.0 * 1024.0),
    )

    return text, perfometer_logarithmic_dual(
        read_bytes,
        "#60e0a0",
        write_bytes,
        "#60a0e0",
        5000000,
        10,
    )


perfometers["check_mk-winperf_phydisk"] = perfometer_check_mk_diskstat
perfometers["check_mk-hpux_lunstats"] = perfometer_check_mk_diskstat
perfometers["check_mk-aix_diskiod"] = perfometer_check_mk_diskstat
perfometers["check_mk-mysql.innodb_io"] = perfometer_check_mk_diskstat
perfometers["check_mk-esx_vsphere_counters.diskio"] = perfometer_check_mk_diskstat
perfometers["check_mk-emcvnx_disks"] = perfometer_check_mk_diskstat
perfometers["check_mk-ibm_svc_nodestats.diskio"] = perfometer_check_mk_diskstat
perfometers["check_mk-ibm_svc_systemstats.diskio"] = perfometer_check_mk_diskstat


def perfometer_check_mk_iops_r_w(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    iops_r = float(perf_data[0][1])
    iops_w = float(perf_data[1][1])
    text = "%.0f IO/s %.0f IO/s" % (iops_r, iops_w)

    return text, perfometer_logarithmic_dual(iops_r, "#60e0a0", iops_w, "#60a0e0", 100000, 10)


perfometers["check_mk-ibm_svc_nodestats.iops"] = perfometer_check_mk_iops_r_w
perfometers["check_mk-ibm_svc_systemstats.iops"] = perfometer_check_mk_iops_r_w


def perfometer_check_mk_disk_latency_r_w(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    latency_r = float(perf_data[0][1])
    latency_w = float(perf_data[1][1])
    text = "%.1f ms %.1f ms" % (latency_r, latency_w)

    return text, perfometer_logarithmic_dual(latency_r, "#60e0a0", latency_w, "#60a0e0", 20, 10)


perfometers["check_mk-ibm_svc_nodestats.disk_latency"] = perfometer_check_mk_disk_latency_r_w
perfometers["check_mk-ibm_svc_systemstats.disk_latency"] = perfometer_check_mk_disk_latency_r_w


def perfometer_in_out_mb_per_sec(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    read_mbit = float(perf_data[0][1]) / 131072
    write_mbit = float(perf_data[1][1]) / 131072

    text = "%-.2fMb/s  %-.2fMb/s" % (read_mbit, write_mbit)

    return text, perfometer_logarithmic_dual(read_mbit, "#30d050", write_mbit, "#0060c0", 100, 10)


perfometers["check_mk-openvpn_clients"] = perfometer_in_out_mb_per_sec


def perfometer_check_mk_hba(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    if len(perf_data) < 2:
        return None

    read_blocks = int(perf_data[0][1])
    write_blocks = int(perf_data[1][1])

    text = "%d/s  %d/s" % (read_blocks, write_blocks)

    return text, perfometer_logarithmic_dual(
        read_blocks, "#30d050", write_blocks, "#0060c0", 100000, 2
    )


perfometers["check_mk-emcvnx_hba"] = perfometer_check_mk_hba


def perfometer_check_mk_iops(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    iops = int(perf_data[0][1])
    text = "%d/s" % iops

    return text, perfometer_logarithmic(iops, 100000, 2, "#30d050")


perfometers["check_mk-emc_isilon_iops"] = perfometer_check_mk_iops


def perfometer_check_mk_printer_supply(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    left = utils.savefloat(perf_data[0][1])
    maxi = utils.savefloat(perf_data[0][6])
    if maxi < 0:
        return None  # Printer does not supply a max value

    # If there is no 100% given, calculate the percentage
    if maxi not in (0.0, 100.0):
        left = left * 100.0 / maxi

    s = row["service_description"].lower()

    if "black" in s or ("ink" not in s and s[-1] == "k"):
        colors = ["#000000", "#6E6F00", "#6F0000"]
    elif "magenta" in s or s[-1] == "m":
        colors = ["#FC00FF", "#FC7FFF", "#FEDFFF"]
    elif "yellow" in s or s[-1] == "y":
        colors = ["#FFFF00", "#FEFF7F", "#FFFFCF"]
    elif "cyan" in s or s[-1] == "c":
        colors = ["#00FFFF", "#7FFFFF", "#DFFFFF"]
    else:
        colors = ["#CCCCCC", "#ffff00", "#ff0000"]

    st = min(2, row["service_state"])
    color = colors[st]

    return "%.0f%%" % left, perfometer_linear(left, color)


perfometers["check_mk-printer_supply"] = perfometer_check_mk_printer_supply
perfometers["check_mk-printer_supply_ricoh"] = perfometer_check_mk_printer_supply


def perfometer_printer_pages(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    color = "#909090"
    return "%d" % int(perf_data[0][1]), perfometer_logarithmic(perf_data[0][1], 50000, 6, color)


perfometers["check_mk-printer_pages"] = perfometer_printer_pages
perfometers["check_mk-canon_pages"] = perfometer_printer_pages


def perfometer_msx_queues(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    length = int(perf_data[0][1])
    state = row["service_state"]
    if state == 1:
        color = "#ffd020"
    elif state == 2:
        color = "#ff2020"
    else:
        color = "#6090ff"
    return "%d" % length, perfometer_logarithmic(length, 100, 2, color)


perfometers["check_mk-winperf_msx_queues"] = perfometer_msx_queues


def perfometer_fileinfo(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    code = []
    texts = []
    for i, color, base, scale, verbfunc in [
        (0, "#ffcc50", 1000000, 10, lambda v: number_human_readable(v, precision=0)),  # size
        (1, "#ccff50", 3600, 10, cmk.utils.render.approx_age),
    ]:  # age
        val = float(perf_data[i][1])
        code.append(perfometer_logarithmic(val, base, scale, color))
        texts.append(verbfunc(val))
    # perfometer_logarithmic(100, 200, 2, "#883875")
    return (" / ".join(texts), html.render_div(HTML().join(code), class_="stacked"))


def perfometer_fileinfo_groups(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    # No files found in file group yields metrics('count', 'size')
    # Files found in file group yields metrics('count', 'size', 'size_largest', 'size_smallest',
    #                                          'age_oldest', 'age_newest')
    code = []
    texts = []
    perfometer_values = {
        "count": ("#aabb50", 10000, 10, lambda v: ("%d Tot") % v),
        "age_newest": ("#ccff50", 3600, 10, cmk.utils.render.approx_age),
    }
    for name, value, _unit, _min, _max, _warn, _crit in perf_data:
        try:
            color, base, scale, verbfunc = perfometer_values[name]
        except KeyError:
            continue
        value = float(value)
        code.append(perfometer_logarithmic(value, base, scale, color))
        texts.append(verbfunc(value))
    # perfometer_logarithmic(100, 200, 2, "#883875")
    return " / ".join(texts), html.render_div(HTML().join(code), class_="stacked")


perfometers["check_mk-fileinfo"] = perfometer_fileinfo
perfometers["check_mk-fileinfo.groups"] = perfometer_fileinfo_groups


def perfometer_mssql_tablespaces(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    reserved = float(perf_data[2][1])
    data = float(perf_data[3][1])
    indexes = float(perf_data[4][1])
    unused = float(perf_data[5][1])

    data_perc = data / reserved * 100  # fixed: true-division
    indexes_perc = indexes / reserved * 100  # fixed: true-division
    unused_perc = unused / reserved * 100  # fixed: true-division

    return (
        "%.1f%%" % (data_perc + indexes_perc),
        render_perfometer(
            [(data_perc, "#80c0ff"), (indexes_perc, "#00ff80"), (unused_perc, "#f0b000")]
        ),
    )


perfometers["check_mk-mssql_tablespaces"] = perfometer_mssql_tablespaces


def perfometer_mssql_counters_cache_hits(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    perc = float(perf_data[0][1])
    data = [(perc, "#69EA96"), (100 - perc, get_themed_perfometer_bg_color())]
    return "%.1f%%" % perc, render_perfometer(data)


perfometers["check_mk-mssql_counters.cache_hits"] = perfometer_mssql_counters_cache_hits


def perfometer_hpux_tunables(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    _varname, value, _unit, warn, crit, _minival, threshold = perf_data[0]
    if threshold is None:
        return None

    if warn != 0 or crit != 0:
        # go red if we're over crit
        if crit is not None and value > crit:
            color = "#f44"
        # yellow
        elif warn is not None and value > warn:
            color = "#f84"
        else:
            # all green lights
            color = "#2d3"
    else:
        # use a brown-ish color if we have no levels.
        # otherwise it could be "green" all the way to 100%
        color = "#f4a460"

    used = value / threshold * 100  # fixed: true-division

    return "%.0f%%" % (used), perfometer_linear(used, color)


perfometers["check_mk-hpux_tunables.nproc"] = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.maxfiles_lim"] = perfometer_hpux_tunables
# this one still doesn't load. I need more test data to find out why.
perfometers["check_mk-hpux_tunables.semmni"] = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.semmns"] = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.shmseg"] = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.nkthread"] = perfometer_hpux_tunables


# This will probably move to a generic DB one
def perfometer_mysql_capacity(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    color = {0: "#68f", 1: "#ff2", 2: "#f22", 3: "#fa2"}[row["service_state"]]

    size = float(perf_data[0][1])
    # put the vertical middle at 40GB DB size, this makes small databases look small
    # and big ones big. raise every 18 months by Moore's law :)
    median = 40 * 1024 * 1024 * 1024

    return "%s" % number_human_readable(size), perfometer_logarithmic(size, median, 10, color)


perfometers["check_mk-mysql_capacity"] = perfometer_mysql_capacity


def perfometer_vms_system_ios(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    direct = float(perf_data[0][1])
    buffered = float(perf_data[1][1])
    # perfometer_logarithmic(100, 200, 2, "#883875")
    return (
        "%.0f / %.0f" % (direct, buffered),
        html.render_div(
            perfometer_logarithmic(buffered, 10000, 3, "#38b0cf")
            + perfometer_logarithmic(direct, 10000, 3, "#38808f"),
            class_="stacked",
        ),
    )


perfometers["check_mk-vms_system.ios"] = perfometer_vms_system_ios


def perfometer_check_mk_vms_system_procs(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    color = {0: "#a4f", 1: "#ff2", 2: "#f22", 3: "#fa2"}[row["service_state"]]
    return "%d" % int(perf_data[0][1]), perfometer_logarithmic(perf_data[0][1], 100, 2, color)


perfometers["check_mk-vms_system.procs"] = perfometer_check_mk_vms_system_procs


def perfometer_cmc_lcp(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    color = {0: "#68f", 1: "#ff2", 2: "#f22", 3: "#fa2"}[row["service_state"]]
    val = float(perf_data[0][1])
    unit = str(perf_data[0][0])
    return "%.1f %s" % (val, unit), perfometer_logarithmic(val, 4, 2, color)


perfometers["check_mk-cmc_lcp"] = perfometer_cmc_lcp


def perfometer_humidity(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    humidity = float(perf_data[0][1])
    return "%3.1f% %" % humidity, perfometer_linear(humidity, "#6f2")


perfometers["check_mk-carel_uniflair_cooling"] = perfometer_humidity
perfometers["check_mk-cmciii.humidity"] = perfometer_humidity
perfometers["check_mk-allnet_ip_sensoric.humidity"] = perfometer_humidity
perfometers["check_mk-knuerr_rms_humidity"] = perfometer_humidity


def perfometer_eaton(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    return "%s°C" % str(perf[0][1]), perfometer_linear(float(perf[0][1]), "silver")


perfometers["check_mk-ups_eaton_enviroment"] = perfometer_eaton


def perfometer_battery(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    return "%s%%" % str(perf[0][1]), perfometer_linear(float(perf[0][1]), "#C98D5C")


perfometers["check_mk-emc_datadomain_nvbat"] = perfometer_battery


def perfometer_genu_screen(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    value = int(perf[0][1])
    return "%d Sessions" % value, perfometer_logarithmic(value, 5000, 2, "#7109AA")


perfometers["check_mk-genu_pfstate"] = perfometer_genu_screen


def perfometer_simple_mem_usage(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    maxw = perf[0][6]
    used_level = perf[0][1]
    if maxw is None:
        return None
    used_perc = (100.0 / maxw) * used_level
    return "%d%%" % used_perc, perfometer_linear(used_perc, "#20cf80")


perfometers["check_mk-db2_mem"] = perfometer_simple_mem_usage
perfometers["check_mk-esx_vsphere_hostsystem.mem_usage"] = perfometer_simple_mem_usage
perfometers["check_mk-brocade_mlx.module_mem"] = perfometer_simple_mem_usage
perfometers["check_mk-innovaphone_mem"] = perfometer_simple_mem_usage
perfometers["check_mk-juniper_screenos_mem"] = perfometer_simple_mem_usage
perfometers["check_mk-netscaler_mem"] = perfometer_simple_mem_usage
perfometers["check_mk-arris_cmts_mem"] = perfometer_simple_mem_usage
perfometers["check_mk-juniper_trpz_mem"] = perfometer_simple_mem_usage


def perfometer_vmguest_mem_usage(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    used = float(perf[0][1])
    return number_human_readable(used), perfometer_logarithmic(
        used, 1024 * 1024 * 2000, 2, "#20cf80"
    )


perfometers["check_mk-esx_vsphere_vm.mem_usage"] = perfometer_vmguest_mem_usage


def perfometer_esx_vsphere_hostsystem_cpu(
    row: Row, command: str, perf: Perfdata
) -> LegacyPerfometerResult:
    used_perc = float(perf[0][1])
    return "%d%%" % used_perc, perfometer_linear(used_perc, "#60f020")


perfometers["check_mk-esx_vsphere_hostsystem.cpu_usage"] = perfometer_esx_vsphere_hostsystem_cpu


def perfometer_apc_mod_pdu_modules(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = int(utils.savefloat(perf_data[0][1]) * 100)
    return "%skw" % perf_data[0][1], perfometer_logarithmic(value, 500, 2, "#3366CC")


perfometers["check_mk-apc_mod_pdu_modules"] = perfometer_apc_mod_pdu_modules


# Aiflow in l/s
def perfometer_airflow_ls(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = int(float(perf_data[0][1]) * 100)
    return "%sl/s" % perf_data[0][1], perfometer_logarithmic(value, 1000, 2, "#3366cc")


perfometers["check_mk-apc_inrow_airflow"] = perfometer_airflow_ls


# Aiflow Deviation in Percent
def perfometer_airflow_deviation(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = float(perf_data[0][1])
    return "%0.2f%%" % value, perfometer_linear(abs(value), "silver")


perfometers["check_mk-wagner_titanus_topsense.airflow_deviation"] = perfometer_airflow_deviation


def perfometer_fanspeed(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = float(perf_data[0][1])
    return "%.2f%%" % value, perfometer_linear(value, "silver")


perfometers["check_mk-apc_inrow_fanspeed"] = perfometer_fanspeed


def perfometer_fanspeed_logarithmic(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    value = float(perf_data[0][1])
    return "%d rpm" % value, perfometer_logarithmic(value, 5000, 2, "silver")


perfometers["check_mk-hitachi_hnas_fan"] = perfometer_fanspeed_logarithmic
perfometers["check_mk-bintec_sensors.fan"] = perfometer_fanspeed_logarithmic


def perfometer_check_mk_arcserve_backup(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    bytes_ = int(perf_data[2][1])
    text = number_human_readable(bytes_)

    return text, perfometer_logarithmic(bytes_, 1000 * 1024 * 1024 * 1024, 2, "#BDC6DE")


perfometers["check_mk-arcserve_backup"] = perfometer_check_mk_arcserve_backup


def perfometer_check_mk_ibm_svc_host(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    if len(perf_data) < 5:
        return None

    active = int(perf_data[0][1])
    inactive = int(perf_data[1][1])
    degraded = int(perf_data[2][1])
    offline = int(perf_data[3][1])
    other = int(perf_data[4][1])
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


perfometers["check_mk-ibm_svc_host"] = perfometer_check_mk_ibm_svc_host


def perfometer_check_mk_ibm_svc_license(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    if len(perf_data) < 2:
        return None

    licensed = float(perf_data[0][1])
    used = float(perf_data[1][1])
    if used == 0 and licensed == 0:
        return "0 of 0 used", perfometer_linear(100, get_themed_perfometer_bg_color())
    if licensed == 0:
        return "completely unlicensed", perfometer_linear(100, "silver")

    perc_used = used * 100.0 / licensed
    return "%0.2f %% used" % perc_used, perfometer_linear(perc_used, "silver")


perfometers["check_mk-ibm_svc_license"] = perfometer_check_mk_ibm_svc_license


def perfometer_check_mk_ibm_svc_cache(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    write_cache_pc = perf_data[0][1]
    total_cache_pc = perf_data[1][1]
    read_cache_pc = total_cache_pc - write_cache_pc
    free_cache_pc = 100 - total_cache_pc
    data = [
        (write_cache_pc, "#60e0a0"),
        (read_cache_pc, "#60a0e0"),
        (free_cache_pc, get_themed_perfometer_bg_color()),
    ]
    return "%d %% write, %d %% read" % (write_cache_pc, read_cache_pc), render_perfometer(data)


perfometers["check_mk-ibm_svc_nodestats.cache"] = perfometer_check_mk_ibm_svc_cache
perfometers["check_mk-ibm_svc_systemstats.cache"] = perfometer_check_mk_ibm_svc_cache


def perfometer_licenses_percent(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    licenses = perf_data[0][1]
    max_avail = perf_data[0][6]
    if max_avail is None:
        return None
    used_perc = 100.0 * licenses / max_avail
    return "%.0f%% used" % used_perc, perfometer_linear(used_perc, "orange")


perfometers["check_mk-innovaphone_licenses"] = perfometer_licenses_percent
perfometers["check_mk-citrix_licenses"] = perfometer_licenses_percent


def perfometer_smoke_percent(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    used_perc = float(perf[0][1])
    return "%0.6f%%" % used_perc, perfometer_linear(used_perc, "#404040")


perfometers["check_mk-wagner_titanus_topsense.smoke"] = perfometer_smoke_percent


def perfometer_chamber_deviation(row: Row, command: str, perf: Perfdata) -> LegacyPerfometerResult:
    chamber_dev = float(perf[0][1])
    return "%0.6f%%" % chamber_dev, perfometer_linear(chamber_dev, "#000080")


perfometers["check_mk-wagner_titanus_topsense.chamber_deviation"] = perfometer_chamber_deviation


def perfometer_cache_hit_ratio(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    hit_ratio = float(perf_data[0][1])  # is already percentage
    color = "#60f020"
    return "%.2f %% hits" % hit_ratio, perfometer_linear(hit_ratio, color)


perfometers["check_mk-zfs_arc_cache"] = perfometer_cache_hit_ratio
perfometers["check_mk-zfs_arc_cache.l2"] = perfometer_cache_hit_ratio


def perfometer_current(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    display_color = "#50f020"

    value = utils.savefloat(perf_data[0][1])
    crit = utils.savefloat(perf_data[0][4])
    warn = utils.savefloat(perf_data[0][3])
    current_perc = (
        value / crit * 90
    )  # critical is at 90% to allow for more than crit # fixed: true-division

    if value > warn:
        display_color = "#FDC840"
    if value > crit:
        display_color = "#FF0000"

    display_string = "%.1f Ampere" % value
    return display_string, perfometer_linear(current_perc, display_color)


perfometers["check_mk-adva_fsp_current"] = perfometer_current


def perfometer_raritan_pdu_inlet(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    display_color = "#50f020"
    cap = perf_data[0][0].split("-")[-1]
    value = float(perf_data[0][1])
    unit = perf_data[0][2]
    display_str = "%s %s" % (perf_data[0][1], unit)
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


perfometers["check_mk-raritan_pdu_inlet"] = perfometer_raritan_pdu_inlet
perfometers["check_mk-raritan_pdu_inlet_summary"] = perfometer_raritan_pdu_inlet


def perfometer_raritan_pdu_outletcount(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    outletcount = float(perf_data[0][1])
    return "%d" % outletcount, perfometer_logarithmic(outletcount, 20, 2, "#da6")


perfometers["check_mk-raritan_pdu_outletcount"] = perfometer_raritan_pdu_outletcount


def perfometer_allnet_ip_sensoric_tension(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    display_color = "#50f020"
    value = float(perf_data[0][1])
    return str(value), perfometer_linear(value, display_color)


perfometers["check_mk-allnet_ip_sensoric.tension"] = perfometer_allnet_ip_sensoric_tension


def perfometer_pressure(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    pressure = float(perf_data[0][1])
    return "%0.5f bars" % pressure, perfometer_logarithmic(pressure, 1, 2, "#da6")


perfometers["check_mk-allnet_ip_sensoric.pressure"] = perfometer_pressure


def perfometer_voltage(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    color = "#808000"
    value = float(perf_data[0][1])
    return "%0.3f V" % value, perfometer_logarithmic(value, 12, 2, color)


perfometers["check_mk-bintec_sensors.voltage"] = perfometer_voltage


def perfometer_dbmv(row: Row, check_command: str, perf_data: Perfdata) -> LegacyPerfometerResult:
    dbmv = float(perf_data[0][1])
    return "%.1f dBmV" % dbmv, perfometer_logarithmic(dbmv, 50, 2, "#da6")


perfometers["check_mk-docsis_channels_downstream"] = perfometer_dbmv
perfometers["check_mk-docsis_cm_status"] = perfometer_dbmv


def perfometer_veeam_client(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    for graph in perf_data:
        if graph[0] == "avgspeed":
            avgspeed_bytes = int(graph[1])
        if graph[0] == "duration":
            duration_secs = int(graph[1])
    h = perfometer_logarithmic_dual_independent(
        avgspeed_bytes, "#54b948", 10000000, 2, duration_secs, "#2098cb", 500, 2
    )

    avgspeed = cmk.utils.render.fmt_bytes(avgspeed_bytes)
    duration = cmk.utils.render.approx_age(duration_secs)

    return "%s/s&nbsp;&nbsp;&nbsp;%s" % (avgspeed, duration), h


perfometers["check_mk-veeam_client"] = perfometer_veeam_client


def perfometer_ups_outphase(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    load = int(perf_data[2][1])
    return "%d%%" % load, perfometer_linear(load, "#8050ff")


perfometers["check_mk-ups_socomec_outphase"] = perfometer_ups_outphase


def perfometer_el_inphase(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    for data in perf_data:
        if data[0] == "power":
            power = utils.savefloat(data[1])
    return "%.0f W" % power, perfometer_linear(power, "#8050ff")


perfometers["check_mk-raritan_pdu_inlet"] = perfometer_el_inphase
perfometers["check_mk-raritan_pdu_inlet_summary"] = perfometer_el_inphase
perfometers["check_mk-ucs_bladecenter_psu.switch_power"] = perfometer_el_inphase


def perfometer_f5_bigip_vserver(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    connections = int(perf_data[0][1])
    return str(connections), perfometer_logarithmic(connections, 100, 2, "#46a")


perfometers["check_mk-f5_bigip_vserver"] = perfometer_f5_bigip_vserver


def perfometer_nfsiostat(
    row: Row, check_command: str, perf_data: Perfdata
) -> LegacyPerfometerResult:
    for pd in perf_data:
        if pd[0] == "op_s":
            ops = float(pd[1])
            color = "#ff6347"
            return "%d op/s" % ops, perfometer_linear(ops, color)
    return None


perfometers["check_mk-nfsiostat"] = perfometer_nfsiostat
