#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

def perfometer_check_mk(row, check_command, perf_data):
    # make maximum value at 90sec.
    exectime = float(perf_data[0][1])
    perc = min(100.0, exectime / 90.0 * 100)
    if exectime < 10:
        color = "#2d3"
    elif exectime < 30:
        color = "#ff4"
    elif exectime < 60:
        color = "#f84"
    else:
        color = "#f44"

    return "%.1fs" % exectime, perfometer_linear(perc, color)
perfometers["check-mk"] = perfometer_check_mk

def perfometer_check_mk_df(row, check_command, perf_data):
    h = '<table><tr>'
    varname, value, unit, warn, crit, minn, maxx = perf_data[0]
    perc_used = 100 * (float(value) / float(maxx))
    perc_free = 100 - float(perc_used)
    color = { 0: "#0f8", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    h += perfometer_td(perc_used, color)
    h += perfometer_td(perc_free, "white")
    h += "</tr></table>"
    return "%d%%" % perc_used, h

perfometers["check_mk-df"] = perfometer_check_mk_df
perfometers["check_mk-vms_df"] = perfometer_check_mk_df
perfometers["check_mk-vms_diskstat.df"] = perfometer_check_mk_df
perfometers["check_disk"] = perfometer_check_mk_df
perfometers["check_mk-df_netapp"] = perfometer_check_mk_df
perfometers["check_mk-df_netapp32"] = perfometer_check_mk_df
perfometers["check_mk-zfsget"] = perfometer_check_mk_df
perfometers["check_mk-hr_fs"] = perfometer_check_mk_df
perfometers["check_mk-oracle_asm_diskgroup"] = perfometer_check_mk_df
perfometers["check_mk-mysql_capacity"] = perfometer_check_mk_df


def perfometer_check_mk_kernel_util(row, check_command, perf_data):
    h = '<table><tr>'
    h += perfometer_td(perf_data[0][1], "#6f2")
    h += perfometer_td(perf_data[1][1], "#f60")
    h += perfometer_td(perf_data[2][1], "#0bc")
    total = sum([float(p[1]) for p in perf_data])
    h += perfometer_td(100.0 - total, "white")
    h += "</tr></table>"
    return "%d%%" % total, h

perfometers["check_mk-kernel.util"] = perfometer_check_mk_kernel_util
perfometers["check_mk-vms_sys.util"] = perfometer_check_mk_kernel_util
perfometers["check_mk-vms_cpu"] = perfometer_check_mk_kernel_util
perfometers["check_mk-ucd_cpu_util"] = perfometer_check_mk_kernel_util
perfometers["check_mk-lparstat_aix.cpu_util"] = perfometer_check_mk_kernel_util

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
    ram_color, swap_color = {
        0:("#80ff40", "#008030"),
        1:("#ff2", "#dd0"),
        2:("#f44", "#d00"),
        3:("#fa2", "#d80") }[state]
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
perfometers["check_mk-hr_mem"] = perfometer_check_mk_mem_used

def perfometer_check_mk_mem_win(row, check_command, perf_data):
    # only show mem usage, do omit page file
    base_colors = ("#20d060", "#3040d0")
    state = row["service_state"]
    color = { 0: "#20d060", 1: "#ff2", 2: "#f44", 3: "#fa2",}[state]
    ram_total  = float(perf_data[0][6])
    ram_used   = float(perf_data[0][1])
    perc = ram_used / ram_total * 100.0
    return "%d%%" % perc, perfometer_linear(perc, color)

perfometers["check_mk-mem.win"] = perfometer_check_mk_mem_win

def perfometer_check_mk_cpu_threads(row, check_command, perf_data):
    color = { 0: "#a4f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    return "%d" % int(perf_data[0][1]), perfometer_logarithmic(perf_data[0][1], 400, 2, color)

perfometers["check_mk-cpu.threads"] = perfometer_check_mk_cpu_threads

def perfometer_check_mk_kernel(row, check_command, perf_data):
    rate = float(perf_data[0][1])
    return "%.1f/s" % rate, perfometer_logarithmic(rate, 1000, 2, "#da6")

perfometers["check_mk-kernel"] = perfometer_check_mk_kernel


def perfometer_check_mk_cpu_loads(row, check_command, perf_data):
    color = { 0: "#68f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    load = float(perf_data[0][1])
    return "%.1f" % load, perfometer_logarithmic(load, 4, 2, color)


perfometers["check_mk-cpu.loads"] = perfometer_check_mk_cpu_loads
perfometers["check_mk-ucd_cpu_load"] = perfometer_check_mk_cpu_loads

def perfometer_check_mk_ntp(row, check_command, perf_data, unit = "ms"):
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

    return "%.1f %s" % (offset, unit), h

perfometers["check_mk-ntp"]        = perfometer_check_mk_ntp
perfometers["check_mk-ntp.time"]   = perfometer_check_mk_ntp
perfometers["check_mk-systemtime"] = lambda r, c, p: perfometer_check_mk_ntp(r, c, p, "s")

def perfometer_ipmi_sensors(row, check_command, perf_data):
    state = row["service_state"]
    color = { 0: "#39f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[state]
    value = float(perf_data[0][1])
    crit = savefloat(perf_data[0][4])
    if not crit:
        return "%d" % int(value), perfometer_logarithmic(value, 40, 1.2, color)

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
    if perf_data[0][0] == "temp":
        unit = "°C"
    else:
        unit = ""
    return (u"%d%s" % (int(value), unit)), h

perfometers["check_mk-ipmi_sensors"] = perfometer_ipmi_sensors

def perfometer_temperature(row, check_command, perf_data):
    state = row["service_state"]
    color = { 0: "#39f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[state]
    value = float(perf_data[0][1])
    crit = savefloat(perf_data[0][4])
    return u"%d°C" % int(value), perfometer_logarithmic(value, 40, 1.2, color)

perfometers["check_mk-nvidia.temp"] = perfometer_temperature
perfometers["check_mk-cisco_temp_sensor"] = perfometer_temperature
perfometers["check_mk-cisco_temp_perf"] = perfometer_temperature
perfometers["check_mk-cmctc_lcp.temp"] = perfometer_temperature
perfometers["check_mk-cmctc.temp"] = perfometer_temperature
perfometers["check_mk-smart.temp"] = perfometer_temperature
perfometers["check_mk-f5_bigip_temp"] = perfometer_temperature
perfometers["check_mk-hp_proliant_temp"] = perfometer_temperature
perfometers["check_mk-akcp_sensor_temp"] = perfometer_temperature
perfometers["check_mk-fsc_temp"] = perfometer_temperature

def perfometer_blower(row, check_command, perf_data):
    rpm = saveint(perf_data[0][1])
    perc = rpm / 10000.0 * 100.0
    return "%d RPM" % rpm, perfometer_logarithmic(rpm, 2000, 1.5, "#88c")

perfometers["check_mk-cmctc_lcp.blower"] = perfometer_blower

def perfometer_lcp_regulator(row, check_command, perf_data):
    value = saveint(perf_data[0][1])
    return "%d%%" % value, perfometer_linear(value, "#8c8")

perfometers["check_mk-cmctc_lcp.regulator"] = perfometer_lcp_regulator

def perfometer_bandwidth(in_traffic, out_traffic, in_bw, out_bw, unit = "B"):
    txt = []
    have_bw = True
    h = '<table><tr>'
    traffic_multiplier = unit == "B" and 1 or 8
    for name, bytes, bw, color in [
          ("in",  in_traffic,  in_bw,  "#0e6"),
          ("out", out_traffic, out_bw, "#2af") ]:
        if bw > 0.0:
            rrate = bytes / bw
        else:
            have_bw = False
            break
        drate = max(0.02, rrate ** 0.5 ** 0.5)
        rperc = 100 * rrate
        dperc = 100 * drate
        a = perfometer_td(dperc / 2, color)
        b = perfometer_td(50 - dperc/2, "#fff")
        if name == "in":
            h += b + a # white left, color right
        else:
            h += a + b # color right, white left
        txt.append("%.1f%%" % rperc)
    if have_bw:
        h += '</tr></table>'
        return " &nbsp; ".join(txt), h

    # make logarithmic perf-o-meter
    MB = 1000000.0
    text = "%s/s&nbsp;&nbsp;&nbsp;%s/s" % (
        number_human_readable(in_traffic * traffic_multiplier, 1, unit), number_human_readable(out_traffic * traffic_multiplier, 1, unit))

    return text, perfometer_logarithmic_dual(
                 in_traffic, "#0e6", out_traffic, "#2af", 1000000, 5)

def perfometer_check_mk_if(row, check_command, perf_data):
    unit =  "Bit/s" in row["service_plugin_output"] and "Bit" or "B"
    return perfometer_bandwidth(
        in_traffic  = savefloat(perf_data[0][1]),
        out_traffic = savefloat(perf_data[5][1]),
        in_bw     = savefloat(perf_data[0][6]),
        out_bw    = savefloat(perf_data[5][6]),
        unit      = unit
    )

def perfometer_check_mk_brocade_fcport(row, check_command, perf_data):
    return perfometer_bandwidth(
        in_traffic  = savefloat(perf_data[0][1]),
        out_traffic = savefloat(perf_data[1][1]),
        in_bw     = savefloat(perf_data[0][6]),
        out_bw    = savefloat(perf_data[1][6]),
    )

perfometers["check_mk-if"] = perfometer_check_mk_if
perfometers["check_mk-if64"] = perfometer_check_mk_if
perfometers["check_mk-vms_if"] = perfometer_check_mk_if
perfometers["check_mk-if_lancom"] = perfometer_check_mk_if
perfometers["check_mk-lnx_if"] = perfometer_check_mk_if
perfometers["check_mk-hpux_if"] = perfometer_check_mk_if
perfometers["check_mk-mcdata_fcport"] = perfometer_check_mk_if
perfometers["check_mk-brocade_fcport"] = perfometer_check_mk_brocade_fcport

def perfometer_oracle_tablespaces(row, check_command, perf_data):
    current = float(perf_data[0][1])
    used = float(perf_data[1][1])
    max = float(perf_data[2][1])
    used_perc = used / max * 100
    curr_perc = (current / max * 100) - used_perc
    h = '<table><tr>'
    h += perfometer_td(used_perc, "#f0b000");
    h += perfometer_td(curr_perc, "#00ff80");
    h += perfometer_td(100 - used_perc - curr_perc, "#80c0ff");
    h += '</tr></table>'
    return "%.1f%%" % used_perc, h

perfometers["check_mk-oracle_tablespaces"] = perfometer_oracle_tablespaces

def perfometer_oracle_sessions(row, check_command, perf_data):
    if check_command == "check_mk-oracle_sessions":
	color = "#00ff48";
        unit = "";
    else:
	color = "#4800ff";
        unit = "/h";
    value = int(perf_data[0][1]);
    return "%d%s" % (value, unit), perfometer_logarithmic(value, 50, 2, color);

perfometers["check_mk-oracle_sessions"] = perfometer_oracle_sessions
perfometers["check_mk-oracle_logswitches"] = perfometer_oracle_sessions

def perfometer_cpu_utilization(row, check_command, perf_data):
    util = float(perf_data[0][1]) # is already percentage
    color = "#cf2"
    if perf_data[0][3]:
        warn = float(perf_data[0][3])
        crit = float(perf_data[0][4])
        if util < warn:
            color = "#6f2"
        elif util < crit:
            color = "#9f2"

    return "%.0f%%" % util, perfometer_linear(util, color)

#perfometer_linear(perc, color)
perfometers["check_mk-h3c_lanswitch_cpu"] = perfometer_cpu_utilization
perfometers["check_mk-winperf_processor.util"] = perfometer_cpu_utilization

def perfometer_hpux_snmp_cs_cpu(row, check_command, perf_data):
    h = '<table><tr>'
    h += perfometer_td(float(perf_data[0][1]), "#60f020")
    h += perfometer_td(float(perf_data[1][1]), "#ff6000")
    h += perfometer_td(float(perf_data[2][1]), "#00d080")
    h += perfometer_td(float(perf_data[3][1]), "#ffffff")
    h += '</tr></table>'
    sum = float(perf_data[0][1]) + float(perf_data[1][1]) + float(perf_data[2][1])
    return "%.0f%%" % sum, h

perfometers["check_mk-hpux_snmp_cs.cpu"] = perfometer_hpux_snmp_cs_cpu


def perfometer_check_mk_uptime(row, check_command, perf_data):
    days,    rest    = divmod(int(perf_data[0][1]), 60*60*24)
    hours,   rest    = divmod(rest,   60*60)
    minutes, seconds = divmod(rest,      60)

    return "%02dd %02dh %02dm" % (days, hours, minutes), perfometer_logarithmic(perf_data[0][1], 2592000, 2, '#80F000')

perfometers["check_mk-uptime"]      = perfometer_check_mk_uptime
perfometers["check_mk-snmp_uptime"] = perfometer_check_mk_uptime


def perfometer_check_mk_diskstat(row, check_command, perf_data):
    # No Perf-O-Meter for legacy version of diskstat possible
    if len(perf_data) < 2:
        return "", ""

    read_bytes = float(perf_data[0][1])
    write_bytes = float(perf_data[1][1])

    text = "%-.2fM/s  %-.2fM/s" % \
            (read_bytes / (1024*1024.0), write_bytes / (1024*1024.0))

    return text, perfometer_logarithmic_dual(
            read_bytes, "#60e0a0", write_bytes, "#60a0e0", 5000000, 10)

perfometers["check_mk-diskstat"] = perfometer_check_mk_diskstat
perfometers["check_mk-winperf_phydisk"] = perfometer_check_mk_diskstat
perfometers["check_mk-hpux_lunstats"] = perfometer_check_mk_diskstat
perfometers["check_mk-mysql.innodb_io"] = perfometer_check_mk_diskstat


def perfometer_check_mk_printer_supply(row, check_command, perf_data):
    left = savefloat(perf_data[0][1])
    warn = savefloat(perf_data[0][3])
    crit = savefloat(perf_data[0][4])
    mini = savefloat(perf_data[0][5])
    maxi = savefloat(perf_data[0][6])
    if maxi < 0:
        return "", "" # Printer does not supply a max value

    # If there is no 100% given, calculate the percentage
    if maxi != 100.0 and maxi != 0.0:
        left = left * 100 / maxi

    s = row['service_description'].lower()

    fg_color = '#000000'
    if 'black' in s or s[-1] == 'k':
        colors   = [ '#000000', '#6E6F00', '#6F0000' ]
        if left >= 60:
            fg_color = '#ffffff'
    elif 'magenta' in s or s[-1] == 'm':
        colors = [ '#fc00ff', '#FC7FFF', '#FEDFFF' ]
    elif 'yellow' in s or s[-1] == 'y':
        colors = [ '#ffff00', '#FEFF7F', '#FFFFCF' ]
    elif 'cyan' in s or s[-1] == 'c':
        colors = [ '#00ffff', '#7FFFFF', '#DFFFFF' ]
    else:
        colors = [ '#cccccc', '#ffff00', '#ff0000' ]

    st = min(2, row['service_state'])
    color = colors[st]

    return "<font color=\"%s\">%.0f%%</font>" % (fg_color, left), perfometer_linear(left, color)

perfometers["check_mk-printer_supply"] = perfometer_check_mk_printer_supply
perfometers["check_mk-printer_supply_ricon"] = perfometer_check_mk_printer_supply

def perfometer_msx_queues(row, check_command, perf_data):
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

def perfometer_fileinfo(row, check_command, perf_data):
    h = '<div class="stacked">'
    texts = []
    for i, color, base, scale, verbfunc in [
        ( 0, "#ffcc50", 1000000, 10, lambda v: number_human_readable(v, precision=0) ), # size
        ( 1, "#ccff50", 3600, 10,    age_human_readable )]:   # age
        val = float(perf_data[i][1])
        h += perfometer_logarithmic(val, base, scale, color)
        texts.append(verbfunc(val))
    h += '</div>'
    return " / ".join(texts), h #  perfometer_logarithmic(100, 200, 2, "#883875")

def perfometer_fileinfo_groups(row, check_command, perf_data):
    h = '<div class="stacked">'
    texts = []
    for i, color, base, scale, verbfunc in [
        ( 2, "#aabb50", 10000, 10, lambda v: ("%d Tot") % v ), # count
        ( 1, "#ccff50", 3600, 10, age_human_readable )]: #age_newest
        val = float(perf_data[i][1])
        h += perfometer_logarithmic(val, base, scale, color)
        texts.append(verbfunc(val))
    h += '</div>'
    return " / ".join(texts), h #  perfometer_logarithmic(100, 200, 2, "#883875")

perfometers["check_mk-fileinfo"] = perfometer_fileinfo
perfometers["check_mk-fileinfo.groups"] = perfometer_fileinfo_groups

def perfometer_mssql_tablespaces(row, check_command, perf_data):
    size        = float(perf_data[0][1])
    unallocated = float(perf_data[1][1])
    reserved    = float(perf_data[2][1])
    data        = float(perf_data[3][1])
    indexes     = float(perf_data[4][1])
    unused      = float(perf_data[5][1])

    data_perc    = data / reserved * 100
    indexes_perc = indexes / reserved * 100
    unused_perc  = unused / reserved * 100

    h = '<table><tr>'
    h += perfometer_td(data_perc, "#80c0ff");
    h += perfometer_td(indexes_perc, "#00ff80");
    h += perfometer_td(unused_perc, "#f0b000");
    h += '</tr></table>'
    return "%.1f%%" % (data_perc + indexes_perc), h

perfometers["check_mk-mssql_tablespaces"] = perfometer_mssql_tablespaces

def perfometer_mssql_counters_cache_hits(row, check_command, perf_data):
    perc = float(perf_data[0][1])

    h = '<table><tr>'
    h += perfometer_td(perc, "#69EA96");
    h += perfometer_td(100 - perc, "#ffffff");
    h += '</tr></table>'
    return "%.1f%%" % perc, h

perfometers["check_mk-mssql_counters.cache_hits"] = perfometer_mssql_counters_cache_hits



def perfometer_hpux_tunables(row, check_command, perf_data):

    varname, value, unit, warn, crit, minival, threshold = perf_data[0]
    value       = float(value)
    threshold   = float(threshold)


    if warn != "" or crit != "":
        warn = saveint(warn)
        crit = saveint(crit)

        # go red if we're over crit
        if value > crit:
           color = "#f44"
        # yellow
        elif value > warn:
           color = "#f84"
        else:
           # all green lights
           color = "#2d3"
    else:
        # use a brown-ish color if we have no levels.
        # otherwise it could be "green" all the way to 100%
        color = "#f4a460"

    used = value / threshold * 100

    return "%.0f%%" % (used), perfometer_linear(used, color)

perfometers["check_mk-hpux_tunables.nproc"]        = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.nkthread"]     = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.maxfiles_lim"] = perfometer_hpux_tunables
# this one still doesn't load. I need more test data to find out why.
perfometers["check_mk-hpux_tunables.semmni"]       = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.semmns"]       = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.shmseg"]       = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.nkthread"]     = perfometer_hpux_tunables
perfometers["check_mk-hpux_tunables.nkthread"]     = perfometer_hpux_tunables



# This will probably move to a generic DB one
def perfometer_mysql_capacity(row, check_command, perf_data):
    color = { 0: "#68f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]

    size = float(perf_data[0][1])
    # put the vertical middle at 40GB DB size, this makes small databases look small
    # and big ones big. raise every 18 months by Moore's law :)
    median = 40 * 1024 * 1024 * 1024

    return "%s" % number_human_readable(size), perfometer_logarithmic(size, median, 10, color)

perfometers['check_mk-mysql_capacity'] = perfometer_mysql_capacity

def perfometer_vms_system_ios(row, check_command, perf_data):
    h = '<div class="stacked">'
    direct = float(perf_data[0][1])
    buffered = float(perf_data[1][1])
    h += perfometer_logarithmic(buffered, 10000, 3, "#38b0cf")
    h += perfometer_logarithmic(direct, 10000, 3, "#38808f")
    h += '</div>'
    return "%.0f / %.0f" % (direct, buffered), h #  perfometer_logarithmic(100, 200, 2, "#883875")

perfometers["check_mk-vms_system.ios"] = perfometer_vms_system_ios


def perfometer_check_mk_vms_system_procs(row, check_command, perf_data):
    color = { 0: "#a4f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    return "%d" % int(perf_data[0][1]), perfometer_logarithmic(perf_data[0][1], 100, 2, color)

perfometers["check_mk-vms_system.procs"] = perfometer_check_mk_vms_system_procs

def perfometer_cmc_lcp(row, check_command, perf_data):
    color = { 0: "#68f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    val = float(perf_data[0][1])
    unit = str(perf_data[0][0])
    return "%.1f %s" % (val,unit), perfometer_logarithmic(val, 4, 2, color)

perfometers["check_mk-cmc_lcp"] = perfometer_cmc_lcp


def perfometer_carel_uniflair_cooling(row, check_command, perf_data):
    humidity = float(perf_data[0][1])
    return "%3.1f%%" % humidity, perfometer_linear(humidity, '#6f2')

perfometers['check_mk-carel_uniflair_cooling'] = perfometer_carel_uniflair_cooling

def perfometer_eaton(row, command, perf):
    return u"%s°C" % str(perf[0][1]), perfometer_linear(float(perf[0][1]), 'silver')

perfometers['check_mk-ups_eaton_enviroment'] = perfometer_eaton


def perfometer_ups_capacity(row, command, perf):
    return "%0.2f%%" % float(perf[1][1]), perfometer_linear(float(perf[1][1]), '#B2FF7F')

perfometers['check_mk-ups_capacity'] = perfometer_ups_capacity

def perfometer_genu_screen(row, command, perf):
    value = saveint(perf[0][1])
    return "%d Sessions" % value  , perfometer_logarithmic(value, 5000 , 2 , "#7109AA")

perfometers['check_mk-genu_pfstate'] = perfometer_genu_screen

def perfometer_db2_mem(row, command, perf):
    maxw = float(perf[0][6])
    used_level = float(perf[0][1])
    used_perc = (100.0 / maxw) * used_level
    return "%d%% used" % used_perc  , perfometer_linear(used_perc, "#0000FF")

perfometers['check_mk-db2_mem'] = perfometer_db2_mem
