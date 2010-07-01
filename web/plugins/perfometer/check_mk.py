#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
# 
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
# 
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# Perf-O-Meters for Check_MK's checks
#
# They are called with:
# 1. row -> a dictionary of the data row with at least the
#    keys "service_perf_data", "service_state" and "service_check_command"
# 2. The check command (might be extracted from the performance data
#    in a PNP-like manner, e.g if perfdata is "value=10.5;0;100.0;20;30 [check_disk]
# 3. The parsed performance data as a list of 7-tuples of
#    (varname, value, unit, warn, crit, min, max)

def perfometer_check_mk_df(row, check_command, perf_data):
    h = '<table><tr>'
    varname, value, unit, warn, crit, minn, maxx = perf_data[0]
    perc_used = 100 * (float(value) / float(maxx))
    perc_free = 100 - float(perc_used)
    color = { 0: "#0f8", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    h += perfometer_td(perc_used, color)
    h += perfometer_td(perc_free, "white")
    h += "</tr></table>"
    # return "%d%% of %.1fGB used" % (perc_used, float(value)/1024.0), h
    return "%d%%" % perc_used, h
    return "%d%% used" % perc_used, h

perfometers["check_mk-df"] = perfometer_check_mk_df
perfometers["check_mk-vms_df"] = perfometer_check_mk_df
perfometers["check_disk"] = perfometer_check_mk_df


def perfometer_check_mk_kernel_util(row, check_command, perf_data):
    h = '<table><tr>'
    h += perfometer_td(perf_data[0][1], "#f60")
    h += perfometer_td(perf_data[1][1], "#6f2")
    h += perfometer_td(perf_data[2][1], "#0bc")
    total = sum([float(p[1]) for p in perf_data])
    h += perfometer_td(100.0 - total, "white")
    h += "</tr></table>"
    return "%d%%" % total, h

perfometers["check_mk-kernel.util"] = perfometer_check_mk_kernel_util
perfometers["check_mk-vms_sys.util"] = perfometer_check_mk_kernel_util

def perfometer_check_mk_mem_used(row, check_command, perf_data):
    h = '<table><tr>'
    ram_total  = float(perf_data[0][6])
    swap_total = float(perf_data[1][6])
    virt_total = ram_total + swap_total

    ram_used   = float(perf_data[0][1])
    swap_used  = float(perf_data[1][1])
    virt_used  = ram_used + swap_used

    state = row["service_state"]
    # paint used ram and swap
    ram_color, swap_color = { 0: ("#80ff40", "#008030"), 1: ("#ff2", "#dd0"), 2:("#f44", "#d00"), 3:("#fa2", "#d80") }[state]
    h += perfometer_td(100 * ram_used / virt_total, ram_color)
    h += perfometer_td(100 * swap_used / virt_total, swap_color)

    # used virtual memory < ram => show free ram and free total virtual memory
    if virt_used < ram_total:
        h += perfometer_td(100 * (ram_total - virt_used) / virt_total, "#fff")
        h += perfometer_td(100 * (virt_total - ram_total) / virt_total, "#ccc")
    # usage exceeds ram => show only free virtual memory
    else:
        h += perfometer_td(100 * (virt_total - virt_used), "#ccc")
    h += "</tr></table>"
    return "%d%%" % (100 * (virt_used / ram_total)), h

perfometers["check_mk-mem.used"] = perfometer_check_mk_mem_used

# def perfometer_check_mk_kernel(row, check_command, perf_data):
#     return "%d/s" % int(perf_data[0][1]), perfometer_logarithmic(perf_data[0][1], 1000, 10, "#f2a")
# 
# perfometers["check_mk-kernel"] = perfometer_check_mk_kernel

def perfometer_check_mk_cpu_threads(row, check_command, perf_data):
    color = { 0: "#a4f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    return "%d" % int(perf_data[0][1]), perfometer_logarithmic(perf_data[0][1], 400, 2, color)

perfometers["check_mk-cpu.threads"] = perfometer_check_mk_cpu_threads


def perfometer_check_mk_cpu_loads(row, check_command, perf_data):
    color = { 0: "#68f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    load = float(perf_data[0][1]) 
    return "%.1f" % load, perfometer_logarithmic(load, 4, 2, color)


perfometers["check_mk-cpu.loads"] = perfometer_check_mk_cpu_loads

def perfometer_check_mk_ntp(row, check_command, perf_data):
    offset = float(perf_data[0][1])
    absoffset = abs(offset)
    warn = float(perf_data[0][3])
    crit = float(perf_data[0][4])
    max = crit * 2
    if absoffset > max:
        absoffset = max
    rel = 50 * (absoffset / max)

    color = { 0: "#0f8", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    
    h = '<table><tr>'
    if offset > 0:
        h += perfometer_td(50, "#fff")
        h += perfometer_td(rel, color)
        h += perfometer_td(50 - rel, "#fff")
    else:
        h += perfometer_td(50 - rel, "#fff")
        h += perfometer_td(rel, color)
        h += perfometer_td(50, "#fff")
    h += '</tr></table>'

    return "%.1f ms" % offset, h

perfometers["check_mk-ntp"] = perfometer_check_mk_ntp
perfometers["check_mk-ntp.time"] = perfometer_check_mk_ntp

def perfometer_check_mk_ipmi_sensors(row, check_command, perf_data):
    state = row["service_state"]
    color = { 0: "#06f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[state]
    value = float(perf_data[0][1])
    crit = float(perf_data[0][4])
    perc = 100 * value / crit 
    # some sensors get critical if the value is < crit (fans), some if > crit (temp)
    h = '<table><tr>'
    if value <= crit:
        h += perfometer_td(perc, color)
        h += perfometer_td(100 - perc, "#fff")
    elif state == 0: # fan, OK
        m = max(value, 10000.0)
        perc_crit = 100 * crit / m
        perc_value = 100 * (value-crit) / m
        perc_free = 100 * (m - value) / m
        h += perfometer_td(perc_crit, color)
        h += perfometer_td(perc_value, color)
        h += perfometer_td(perc_free, "#fff")
    h += '</tr></table>'
    return "%d" % int(value), h

perfometers["check_mk-ipmi_sensors"] = perfometer_check_mk_ipmi_sensors

        


