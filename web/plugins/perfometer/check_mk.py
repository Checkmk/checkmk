#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

def perfometer_esx_vsphere_datastores(row, check_command, perf_data):
    used_mb        = perf_data[0][1]
    maxx           = perf_data[0][-1]
    # perf data might be incomplete, if trending perfdata is off...
    uncommitted_mb = 0
    for entry in perf_data:
        if entry[0] == "uncommitted":
            uncommitted_mb = entry[1]
            break

    perc_used = 100 * (float(used_mb) / float(maxx))
    perc_uncommitted = 100 * (float(uncommitted_mb) / float(maxx))
    perc_totally_free = 100 - perc_used - perc_uncommitted

    h = '<table><tr>'
    if perc_used + perc_uncommitted <= 100:
        # Regular handling, no overcommitt
        h += perfometer_td(perc_used, "#00ffc6")
        h += perfometer_td(perc_uncommitted, "#eeccff")
        h += perfometer_td(perc_totally_free, "white")
    else:
        # Visualize overcommitted space by scaling to total overcommittment value
        # and drawing the capacity as red line in the perfometer
        total = perc_used + perc_uncommitted
        perc_used_bar = perc_used * 100 / total
        perc_uncommitted_bar = perc_uncommitted * 100 / total
        perc_free = (100 - perc_used) * 100 / total

        h += perfometer_td(perc_used_bar, "#00ffc6")
        h += perfometer_td(perc_free, "#eeccff")
        h += perfometer_td(1, "red") # This line visualizes the capacity
        h += perfometer_td(perc_uncommitted - perc_free, "#eeccff")
    h += "</tr></table>"

    legend = "%0.2f%%" % perc_used
    if uncommitted_mb:
        legend += " (+%0.2f%%)" % perc_uncommitted
    return legend, h

perfometers["check_mk-esx_vsphere_datastores"] = perfometer_esx_vsphere_datastores


def perfometer_check_mk_mem_used(row, check_command, perf_data):
    ram_used = None

    for entry in perf_data:
        # Get total and used RAM
        if entry[0] == "ramused":
            ram_used   = float(entry[1]) # mem.include
            ram_total  = float(entry[6]) # mem.include
        elif entry[0] == "mem_used":
            ram_used   = float(entry[1]) # mem.linux
        elif entry[0] == "mem_total":
            ram_total  = float(entry[1]) # mem.linux

        # Get total and used SWAP
        elif entry[0] == "swapused":
            swap_used   = float(entry[1]) # mem.include
            swap_total  = float(entry[6]) # mem.include
        elif entry[0] == "swap_used":
            swap_used   = float(entry[1]) # mem.linux
        elif entry[0] == "swap_total":
            swap_total  = float(entry[1]) # mem.linux

    if not ram_used:
        return "",""

    virt_total = ram_total + swap_total
    virt_used  = ram_used + swap_used

    # paint used ram and swap
    ram_color, swap_color = "#80ff40", "#008030"

    h = '<table><tr>'
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
perfometers["check_mk-mem.linux"] = perfometer_check_mk_mem_used
perfometers["check_mk-aix_memory"] = perfometer_check_mk_mem_used
perfometers["check_mk-hr_mem"] = perfometer_check_mk_mem_used

def perfometer_check_mk_mem_win(row, check_command, perf_data):
    # only show mem usage, do omit page file
    color = "#5090c0"
    ram_total  = float(perf_data[0][6])
    ram_used   = float(perf_data[0][1])
    perc = ram_used / ram_total * 100.0
    return "%d%%" % perc, perfometer_linear(perc, color)

perfometers["check_mk-mem.win"] = perfometer_check_mk_mem_win

def perfometer_check_mk_kernel(row, check_command, perf_data):
    rate = float(perf_data[0][1])
    return "%.1f/s" % rate, perfometer_logarithmic(rate, 1000, 2, "#da6")

perfometers["check_mk-kernel"] = perfometer_check_mk_kernel


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

    return "%.2f %s" % (offset, unit), h

perfometers["check_mk-ntp"]        = perfometer_check_mk_ntp
perfometers["check_mk-ntp.time"]   = perfometer_check_mk_ntp
perfometers["check_mk-chrony"]     = perfometer_check_mk_ntp
perfometers["check_mk-systemtime"] = lambda r, c, p: perfometer_check_mk_ntp(r, c, p, "s")

def perfometer_ipmi_sensors(row, check_command, perf_data):
    state = row["service_state"]
    color = "#39f"
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
    color = "#39f"
    value = float(perf_data[0][1])
    return u"%d °C" % int(value), perfometer_logarithmic(value, 40, 1.2, color)

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
perfometers["check_mk-netscaler_health.temp"]  = perfometer_temperature
perfometers["check_mk-kentix_temp"] = perfometer_temperature
perfometers["check_mk-ucs_bladecenter_fans.temp"] = perfometer_temperature
perfometers["check_mk-ucs_bladecenter_psu.chassis_temp"] = perfometer_temperature
perfometers["check_mk-cisco_temperature"] = perfometer_temperature

def perfometer_temperature_multi(row, check_command, perf_data):
    display_value = -1
    display_color = "#60f020"

    for sensor, value, uom, warn, crit, min, max in perf_data:
        value=saveint(value)
        if value > display_value:
            display_value=value

    if display_value > saveint(warn):
        display_color = "#FFC840"
    if display_value > saveint(crit):
        display_color = "#FF0000"

    display_string = "%s °C" % display_value
    return display_string, perfometer_linear(display_value, display_color)

perfometers["check_mk-brocade_mlx_temp"] = perfometer_temperature_multi

def perfometer_power(row, check_command, perf_data):
    display_color = "#60f020"

    value=savefloat(perf_data[0][1])
    crit=savefloat(perf_data[0][4])
    warn=savefloat(perf_data[0][3])
    power_perc = value/crit*90 # critical is at 90% to allow for more than crit

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

def perfometer_power_simple(row, check_command, perf_data):
    watt = int(perf_data[0][1])
    text = "%s Watt" % watt
    return text, perfometer_logarithmic(watt, 150, 2, "#60f020")

perfometers["check_mk-ibm_svc_enclosurestats.power"] = perfometer_power_simple
perfometers["check_mk-sentry_pdu"] = perfometer_power_simple

def perfometer_users(row, check_command, perf_data):
    state = row["service_state"]
    color = "#39f"
    value = float(perf_data[0][1])
    crit = savefloat(perf_data[0][4])
    return u"%d users" % int(value), perfometer_logarithmic(value, 50, 2, color)

perfometers["check_mk-hitachi_hnas_cifs"] = perfometer_users

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

def perfometer_check_mk_fc_port(row, check_command, perf_data):
    unit = "B"
    return perfometer_bandwidth(
        in_traffic  = savefloat(perf_data[0][1]),
        out_traffic = savefloat(perf_data[1][1]),
        in_bw     = savefloat(perf_data[0][6]),
        out_bw    = savefloat(perf_data[1][6]),
        unit      = unit
    )
perfometers["check_mk-fc_port"] = perfometer_check_mk_fc_port


def perfometer_check_mk_brocade_fcport(row, check_command, perf_data):
    return perfometer_bandwidth(
        in_traffic  = savefloat(perf_data[0][1]),
        out_traffic = savefloat(perf_data[1][1]),
        in_bw     = savefloat(perf_data[0][6]),
        out_bw    = savefloat(perf_data[1][6]),
    )

perfometers["check_mk-brocade_fcport"] = perfometer_check_mk_brocade_fcport
perfometers["check_mk-qlogic_fcport"] = perfometer_check_mk_brocade_fcport

def perfometer_check_mk_cisco_qos(row, check_command, perf_data):
    unit =  "Bit/s" in row["service_plugin_output"] and "Bit" or "B"
    return perfometer_bandwidth(
        in_traffic  = savefloat(perf_data[0][1]),
        out_traffic = savefloat(perf_data[1][1]),
        in_bw     = savefloat(perf_data[0][5])  ,
        out_bw    = savefloat(perf_data[1][5])  ,
        unit      = unit
    )

perfometers["check_mk-cisco_qos"] = perfometer_check_mk_cisco_qos


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

def perfometer_check_oracle_dataguard_stats(row, check_command, perf_data):
    perfdata_found = False
    perfdata1 = ''

    for data in perf_data:
        if data[0] == "apply_lag":
            color = '#80F000'

            perfdata_found = True
            days,    rest    = divmod(int(data[1]), 60*60*24)
            hours,   rest    = divmod(rest,   60*60)
            minutes, seconds = divmod(rest,      60)
            perfdata1 = data[1]


    if perfdata_found == False:
        days = 0
        hours = 0
        minutes = 0
        color = "#008f48";

    return "%02dd %02dh %02dm" % (days, hours, minutes), perfometer_logarithmic(perfdata1, 2592000, 2, color)

perfometers["check_mk-oracle_dataguard_stats"]      = perfometer_check_oracle_dataguard_stats

def perfometer_oracle_sessions(row, check_command, perf_data):
    if check_command != "check_mk-oracle_sessions":
	color = "#008f48";
        unit = "";
    else:
	color = "#4800ff";
        unit = "/h";
    value = int(perf_data[0][1]);
    return "%d%s" % (value, unit), perfometer_logarithmic(value, 50, 2, color);

perfometers["check_mk-oracle_sessions"] = perfometer_oracle_sessions
perfometers["check_mk-oracle_logswitches"] = perfometer_oracle_sessions
perfometers["check_mk-oracle_processes"] = perfometer_oracle_sessions

def perfometer_cpu_utilization(row, check_command, perf_data):
    util = float(perf_data[0][1]) # is already percentage
    color = "#60c080"
    return "%.0f %%" % util, perfometer_linear(util, color)

#perfometer_linear(perc, color)
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

def perfometer_ps_perf(row, check_command, perf_data):
    perf_dict = dict([(p[0], float(p[1])) for p in perf_data])
    try:
        perc = perf_dict["pcpu"]
        return "%.1f%%" % perc, perfometer_linear(perc, "#30ff80")
    except:
        return "", ""

perfometers["check_mk-ps"] = perfometer_ps_perf
perfometers["check_mk-ps.perf"] = perfometer_ps_perf


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
    seconds = int(float(perf_data[0][1]))
    days,    rest    = divmod(seconds, 60*60*24)
    hours,   rest    = divmod(rest,   60*60)
    minutes, seconds = divmod(rest,      60)

    return "%02dd %02dh %02dm" % (days, hours, minutes), perfometer_logarithmic(seconds, 2592000.0, 2, '#80F000')

perfometers["check_mk-uptime"]      = perfometer_check_mk_uptime
perfometers["check_mk-snmp_uptime"] = perfometer_check_mk_uptime
perfometers["check_mk-esx_vsphere_counters.uptime"] = perfometer_check_mk_uptime
perfometers["check_mk-oracle_instance"] = perfometer_check_mk_uptime


def perfometer_check_mk_diskstat(row, check_command, perf_data):
    # No Perf-O-Meter for legacy version of diskstat possible
    if len(perf_data) < 2:
        return "", ""

    read_bytes = float(perf_data[0][1])
    write_bytes = float(perf_data[1][1])

    text = "%-.2f M/s  %-.2f M/s" % \
            (read_bytes / (1024*1024.0), write_bytes / (1024*1024.0))

    return text, perfometer_logarithmic_dual(
            read_bytes, "#60e0a0", write_bytes, "#60a0e0", 5000000, 10)

perfometers["check_mk-diskstat"] = perfometer_check_mk_diskstat
perfometers["check_mk-winperf_phydisk"] = perfometer_check_mk_diskstat
perfometers["check_mk-hpux_lunstats"] = perfometer_check_mk_diskstat
perfometers["check_mk-aix_diskiod"] = perfometer_check_mk_diskstat
perfometers["check_mk-mysql.innodb_io"] = perfometer_check_mk_diskstat
perfometers["check_mk-esx_vsphere_counters.diskio"] = perfometer_check_mk_diskstat
perfometers["check_mk-emcvnx_disks"] = perfometer_check_mk_diskstat
perfometers["check_mk-ibm_svc_nodestats.diskio"] = perfometer_check_mk_diskstat
perfometers["check_mk-ibm_svc_systemstats.diskio"] = perfometer_check_mk_diskstat

def perfometer_check_mk_iops_r_w(row, check_command, perf_data):
    iops_r = float(perf_data[0][1])
    iops_w = float(perf_data[1][1])
    text = "%.0f IO/s %.0f IO/s" % (iops_r, iops_w)

    return text, perfometer_logarithmic_dual(
            iops_r, "#60e0a0", iops_w, "#60a0e0", 100000, 10)
perfometers["check_mk-ibm_svc_nodestats.iops"] = perfometer_check_mk_iops_r_w
perfometers["check_mk-ibm_svc_systemstats.iops"] = perfometer_check_mk_iops_r_w

def perfometer_check_mk_disk_latency_r_w(row, check_command, perf_data):
    latency_r = float(perf_data[0][1])
    latency_w = float(perf_data[1][1])
    text = "%.1f ms %.1f ms" % (latency_r, latency_w)

    return text, perfometer_logarithmic_dual(
            latency_r, "#60e0a0", latency_w, "#60a0e0", 20, 10)
perfometers["check_mk-ibm_svc_nodestats.disk_latency"] = perfometer_check_mk_disk_latency_r_w
perfometers["check_mk-ibm_svc_systemstats.disk_latency"] = perfometer_check_mk_disk_latency_r_w

def perfometer_in_out_mb_per_sec(row, check_command, perf_data):
    read_mbit = float(perf_data[0][1]) / 131072
    write_mbit = float(perf_data[1][1]) / 131072

    text = "%-.2fMb/s  %-.2fMb/s" % (read_mbit, write_mbit)

    return text, perfometer_logarithmic_dual(
            read_mbit, "#30d050", write_mbit, "#0060c0", 100, 10)
perfometers["check_mk-openvpn_clients"] = perfometer_in_out_mb_per_sec

def perfometer_check_mk_hba(row, check_command, perf_data):
    if len(perf_data) < 2:
        return "", ""

    read_blocks = int(perf_data[0][1])
    write_blocks = int(perf_data[1][1])

    text = "%d/s  %d/s" % (read_blocks, write_blocks)

    return text, perfometer_logarithmic_dual(
            read_blocks, "#30d050", write_blocks, "#0060c0", 100000, 2)
perfometers["check_mk-emcvnx_hba"] = perfometer_check_mk_hba

def perfometer_check_mk_iops(row, check_command, perf_data):
    iops = int(perf_data[0][1])
    text = "%d/s" % iops

    return text, perfometer_logarithmic(iops, 100000, 2, "#30d050")
perfometers["check_mk-emc_isilon_iops"] = perfometer_check_mk_iops

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
    if 'black' in s or ("ink" not in s and s[-1] == 'k'):
        colors   = [ '#000000', '#6E6F00', '#6F0000' ]
        if left >= 60:
            fg_color = '#FFFFFF'
    elif 'magenta' in s or s[-1] == 'm':
        colors = [ '#FC00FF', '#FC7FFF', '#FEDFFF' ]
    elif 'yellow' in s or s[-1] == 'y':
        colors = [ '#FFFF00', '#FEFF7F', '#FFFFCF' ]
    elif 'cyan' in s or s[-1] == 'c':
        colors = [ '#00FFFF', '#7FFFFF', '#DFFFFF' ]
    else:
        colors = [ '#CCCCCC', '#ffff00', '#ff0000' ]

    st = min(2, row['service_state'])
    color = colors[st]

    return "<font color=\"%s\">%.0f%%</font>" % (fg_color, left), perfometer_linear(left, color)

perfometers["check_mk-printer_supply"] = perfometer_check_mk_printer_supply
perfometers["check_mk-printer_supply_ricoh"] = perfometer_check_mk_printer_supply

def perfometer_printer_pages(row, check_command, perf_data):
    color = "#909090"
    return "%d" % int(perf_data[0][1]), perfometer_logarithmic(perf_data[0][1], 50000, 6, color)

perfometers["check_mk-printer_pages"] = perfometer_printer_pages
perfometers["check_mk-canon_pages"] = perfometer_printer_pages

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


def perfometer_humidity(row, check_command, perf_data):
    humidity = float(perf_data[0][1])
    return "%3.1f% %" % humidity, perfometer_linear(humidity, '#6f2')

perfometers['check_mk-carel_uniflair_cooling'] = perfometer_humidity
perfometers['check_mk-cmciii.humidity'] = perfometer_humidity
perfometers['check_mk-allnet_ip_sensoric.humidity'] = perfometer_humidity
perfometers['check_mk-knuerr_rms_humidity'] = perfometer_humidity

def perfometer_eaton(row, command, perf):
    return u"%s°C" % str(perf[0][1]), perfometer_linear(float(perf[0][1]), 'silver')

perfometers['check_mk-ups_eaton_enviroment'] = perfometer_eaton

def perfometer_battery(row, command, perf):
    return u"%s%%" % str(perf[0][1]), perfometer_linear(float(perf[0][1]), '#C98D5C')

perfometers['check_mk-emc_datadomain_nvbat'] = perfometer_battery

def perfometer_ups_capacity(row, command, perf):
    return "%0.2f%%" % float(perf[1][1]), perfometer_linear(float(perf[1][1]), '#B2FF7F')

perfometers['check_mk-ups_capacity'] = perfometer_ups_capacity

def perfometer_genu_screen(row, command, perf):
    value = saveint(perf[0][1])
    return "%d Sessions" % value  , perfometer_logarithmic(value, 5000 , 2 , "#7109AA")

perfometers['check_mk-genu_pfstate'] = perfometer_genu_screen

def perfometer_simple_mem_usage(row, command, perf):
    maxw = float(perf[0][6])
    used_level = float(perf[0][1])
    used_perc = (100.0 / maxw) * used_level
    return "%d%%" % used_perc  , perfometer_linear(used_perc, "#20cf80")

perfometers['check_mk-db2_mem'] = perfometer_simple_mem_usage
perfometers['check_mk-esx_vsphere_hostsystem.mem_usage'] = perfometer_simple_mem_usage
perfometers['check_mk-brocade_mlx.module_mem'] = perfometer_simple_mem_usage
perfometers['check_mk-innovaphone_mem'] = perfometer_simple_mem_usage
perfometers['check_mk-juniper_screenos_mem'] = perfometer_simple_mem_usage
perfometers['check_mk-netscaler_mem'] = perfometer_simple_mem_usage
perfometers['check_mk-arris_cmts_mem'] = perfometer_simple_mem_usage
perfometers["check_mk-juniper_trpz_mem"] = perfometer_simple_mem_usage

def perfometer_vmguest_mem_usage(row, command, perf):
    used = float(perf[0][1])
    return number_human_readable(used), perfometer_logarithmic(used, 1024*1024*2000, 2, "#20cf80")

perfometers['check_mk-esx_vsphere_vm.mem_usage'] = perfometer_vmguest_mem_usage

def perfometer_esx_vsphere_hostsystem_cpu(row, command, perf):
    used_perc = float(perf[0][1])
    return "%d%%" % used_perc, perfometer_linear(used_perc, "#60f020")

perfometers['check_mk-esx_vsphere_hostsystem.cpu_usage'] = perfometer_esx_vsphere_hostsystem_cpu

def perfometer_mq_queues(row, command, perf):
    size = int(perf[0][1])
    return "%s Messages" % size, perfometer_logarithmic(size, 1, 2, "#701141")

perfometers['check_mk-mq_queues'] = perfometer_mq_queues
perfometers['check_mk-websphere_mq_channels'] = perfometer_mq_queues
perfometers['check_mk-websphere_mq_queues'] = perfometer_mq_queues

def perfometer_apc_mod_pdu_modules(row, check_command, perf_data):
    value = int(savefloat(perf_data[0][1]) * 100)
    return "%skw" % perf_data[0][1], perfometer_logarithmic(value, 500, 2, "#3366CC")

perfometers["check_mk-apc_mod_pdu_modules"] = perfometer_apc_mod_pdu_modules

# Aiflow in l/s
def perfometer_airflow_ls(row, check_command, perf_data):
    value = int(float(perf_data[0][1])*100)
    return "%sl/s" % perf_data[0][1], perfometer_logarithmic(value, 1000, 2, '#3366cc')

perfometers["check_mk-apc_inrow_airflow"] = perfometer_airflow_ls

# Aiflow Deviation in Percent
def perfometer_airflow_deviation(row, check_command, perf_data):
    value = float(perf_data[0][1])
    return "%0.2f%%" % value, perfometer_linear(abs(value), "silver")

perfometers["check_mk-wagner_titanus_topsense.airflow_deviation"] = perfometer_airflow_deviation

def perfometer_fanspeed(row, check_command, perf_data):
    value = float(perf_data[0][1])
    return "%.2f%%" % value, perfometer_linear(value, "silver")

perfometers["check_mk-apc_inrow_fanspeed"]  = perfometer_fanspeed

def perfometer_fanspeed_logarithmic(row, check_command, perf_data):
    value = float(perf_data[0][1])
    return "%d rpm" % value, perfometer_logarithmic(value, 5000, 2, "silver")

perfometers["check_mk-hitachi_hnas_fan"]  = perfometer_fanspeed_logarithmic
perfometers["check_mk-bintec_sensors.fan"]  = perfometer_fanspeed_logarithmic

def perfometer_check_mk_arcserve_backup(row, check_command, perf_data):
    bytes = int(perf_data[2][1])
    text = number_human_readable(bytes)

    return text, perfometer_logarithmic(bytes, 1000 * 1024 * 1024 * 1024, 2, "#BDC6DE")

perfometers["check_mk-arcserve_backup"] = perfometer_check_mk_arcserve_backup

def perfometer_check_mk_ibm_svc_host(row, check_command, perf_data):
    if len(perf_data) < 5:
        return "", ""

    h = '<table><tr>'
    active   = int(perf_data[0][1])
    inactive = int(perf_data[1][1])
    degraded = int(perf_data[2][1])
    offline  = int(perf_data[3][1])
    other    = int(perf_data[4][1])
    total    = active + inactive + degraded + offline + other
    if active > 0:
        perc_active   = 100 * active   / total
        h += perfometer_td(perc_active,   "#008000")
    if inactive > 0:
        perc_inactive = 100 * inactive / total
        h += perfometer_td(perc_inactive, "#0000FF")
    if degraded > 0:
        perc_degraded = 100 * degraded / total
        h += perfometer_td(perc_degraded, "#F84")
    if offline > 0:
        perc_offline  = 100 * offline  / total
        h += perfometer_td(perc_offline,  "#FF0000")
    if other > 0:
        perc_other    = 100 * other    / total
        h += perfometer_td(perc_other,    "#000000")
    if total == 0:
        h += perfometer_td(100,    "white")
    h += "</tr></table>"
    return "%d active" % active, h

perfometers["check_mk-ibm_svc_host"] = perfometer_check_mk_ibm_svc_host

def perfometer_check_mk_ibm_svc_license(row, check_command, perf_data):
    if len(perf_data) < 2:
        return "", ""

    licensed = float(perf_data[0][1])
    used     = float(perf_data[1][1])
    if used == 0 and licensed == 0:
        return "0 of 0 used", perfometer_linear(100, "white")
    elif licensed == 0:
        return "completely unlicensed", perfometer_linear(100, "silver")
    else:
        perc_used = 100 * used / licensed
        return "%0.2f %% used" % perc_used, perfometer_linear(perc_used, "silver")

perfometers["check_mk-ibm_svc_license"] = perfometer_check_mk_ibm_svc_license

def perfometer_check_mk_ibm_svc_cache(row, check_command, perf_data):
    h = '<table><tr>'
    write_cache_pc = int(perf_data[0][1])
    total_cache_pc = int(perf_data[1][1])
    read_cache_pc = total_cache_pc - write_cache_pc
    free_cache_pc = 100 - total_cache_pc
    h += perfometer_td(write_cache_pc, "#60e0a0")
    h += perfometer_td(read_cache_pc,  "#60a0e0")
    h += perfometer_td(free_cache_pc,  "white")
    h += "</tr></table>"
    return "%d %% write, %d %% read" % (write_cache_pc, read_cache_pc), h
perfometers["check_mk-ibm_svc_nodestats.cache"] = perfometer_check_mk_ibm_svc_cache
perfometers["check_mk-ibm_svc_systemstats.cache"] = perfometer_check_mk_ibm_svc_cache


def perfometer_licenses_percent(row, check_command, perf_data):
    licenses = float(perf_data[0][1])
    max_avail = float(perf_data[0][6])
    used_perc = 100.0 * licenses / max_avail
    return "%.0f%% used" % used_perc, perfometer_linear( used_perc, 'orange' )

perfometers['check_mk-innovaphone_licenses'] = perfometer_licenses_percent
perfometers['check_mk-citrix_licenses'] = perfometer_licenses_percent

def perfometer_smoke_percent(row, command, perf):
    used_perc = float(perf[0][1])
    return "%0.6f%%" % used_perc, perfometer_linear(used_perc, "#404040")

perfometers['check_mk-wagner_titanus_topsense.smoke'] = perfometer_smoke_percent

def perfometer_chamber_deviation(row, command, perf):
    chamber_dev = float(perf[0][1])
    return "%0.6f%%" % chamber_dev, perfometer_linear(chamber_dev, "#000080")

perfometers['check_mk-wagner_titanus_topsense.chamber_deviation'] = perfometer_chamber_deviation

def perfometer_cache_hit_ratio(row, check_command, perf_data):
    hit_ratio = float(perf_data[0][1]) # is already percentage
    color = "#60f020"
    return "%.2f %% hits" % hit_ratio, perfometer_linear(hit_ratio, color)

perfometers["check_mk-zfs_arc_cache"] = perfometer_cache_hit_ratio
perfometers["check_mk-zfs_arc_cache.l2"] = perfometer_cache_hit_ratio

def perfometer_current(row, check_command, perf_data):
    display_color = "#50f020"

    value=savefloat(perf_data[0][1])
    crit=savefloat(perf_data[0][4])
    warn=savefloat(perf_data[0][3])
    current_perc = value/crit*90 # critical is at 90% to allow for more than crit

    if value > warn:
        display_color = "#FDC840"
    if value > crit:
        display_color = "#FF0000"

    display_string = "%.1f Ampere" % value
    return display_string, perfometer_linear(current_perc, display_color)

perfometers["check_mk-adva_fsp_current"] = perfometer_current

def perfometer_raritan_pdu_inlet(row, check_command, perf_data):
    display_color = "#50f020"
    cap = perf_data[0][0].split('-')[-1]
    value = float(perf_data[0][1])
    unit = perf_data[0][2]
    display_str = perf_data[0][1] + " " + unit

    if cap.startswith("rmsCurrent"):
        return display_str, perfometer_logarithmic(value, 1, 2, display_color)
    elif cap.startswith("unbalancedCurrent"):
        return display_str, perfometer_linear(value, display_color)
    elif cap.startswith("rmsVoltage"):
        return display_str, perfometer_logarithmic(value, 500, 2, display_color)
    elif cap.startswith("activePower"):
        return display_str, perfometer_logarithmic(value, 20, 2, display_color)
    elif cap.startswith("apparentPower"):
        return display_str, perfometer_logarithmic(value, 20, 2, display_color)
    elif cap.startswith("powerFactor"):
        return display_str, perfometer_linear(value * 100, display_color)
    elif cap.startswith("activeEnergy"):
        return display_str, perfometer_logarithmic(value, 100000, 2, display_color)
    elif cap.startswith("apparentEnergy"):
        return display_str, perfometer_logarithmic(value, 100000, 2, display_color)

    return "unimplemented" , perfometer_linear(0, "#ffffff")

perfometers["check_mk-raritan_pdu_inlet"] = perfometer_raritan_pdu_inlet
perfometers["check_mk-raritan_pdu_inlet_summary"] = perfometer_raritan_pdu_inlet


def perfometer_raritan_pdu_outletcount(row, check_command, perf_data):
    outletcount = float(perf_data[0][1])
    return "%d" % outletcount, perfometer_logarithmic(outletcount, 20, 2, "#da6")

perfometers["check_mk-raritan_pdu_outletcount"] = perfometer_raritan_pdu_outletcount

def perfometer_allnet_ip_sensoric_tension(row, check_command, perf_data):
    display_color = "#50f020"
    value = float(perf_data[0][1])
    return value, perfometer_linear(value, display_color)

perfometers["check_mk-allnet_ip_sensoric.tension"] = perfometer_allnet_ip_sensoric_tension

def perfometer_pressure(row, check_command, perf_data):
    pressure = float(perf_data[0][1])
    return "%0.5f bars" % pressure, perfometer_logarithmic(pressure, 1, 2, "#da6")

perfometers['check_mk-allnet_ip_sensoric.pressure'] = perfometer_pressure

def perfometer_voltage(row, check_command, perf_data):
    color = "#808000"
    value = float(perf_data[0][1])
    return "%0.3f V" % value, perfometer_logarithmic(value, 12, 2, color)

perfometers["check_mk-bintec_sensors.voltage"] = perfometer_voltage

def perfometer_dbmv(row, check_command, perf_data):
    dbmv = float(perf_data[0][1])
    return "%.1f dBmV" % dbmv, perfometer_logarithmic(dbmv, 50, 2, "#da6")

perfometers["check_mk-docsis_channels_downstream"] = perfometer_dbmv
perfometers["check_mk-docsis_cm_status"] = perfometer_dbmv

def perfometer_veeam_client(row, check_command, perf_data):
    for graph in perf_data:
        if graph[0] == "avgspeed":
            avgspeed_bytes = int(graph[1])
        if graph[0] == "duration":
            duration_secs = int(graph[1])
    h = perfometer_logarithmic_dual_independent(avgspeed_bytes, '#54b948', 10000000, 2, duration_secs, '#2098cb', 500, 2)

    avgspeed = bytes_human_readable(avgspeed_bytes)
    # Return Value always as minutes
    duration = age_human_readable(duration_secs, True)

    return "%s/s&nbsp;&nbsp;&nbsp;%s" % (avgspeed, duration), h

perfometers["check_mk-veeam_client"] = perfometer_veeam_client

def perfometer_ups_outphase(row, check_command, perf_data):
    load = saveint(perf_data[2][1])
    return "%d%%" % load, perfometer_linear(load, "#8050ff")

perfometers["check_mk-ups_socomec_outphase"] = perfometer_ups_outphase

def perfometer_el_inphase(row, check_command, perf_data):
    for data in perf_data:
        if data[0] == "power":
            power = savefloat(data[1])
    return "%.0f W" % power, perfometer_linear(power, "#8050ff")

perfometers["check_mk-raritan_pdu_inlet"] = perfometer_el_inphase
perfometers["check_mk-raritan_pdu_inlet_summary"] = perfometer_el_inphase
perfometers["check_mk-ucs_bladecenter_psu.switch_power"] = perfometer_el_inphase

def perfometer_f5_bigip_vserver(row, check_command, perf_data):
    connections = int(perf_data[0][1])
    return str(connections), perfometer_logarithmic(connections, 100, 2, "#46a")

perfometers["check_mk-f5_bigip_vserver"] = perfometer_f5_bigip_vserver


#.
#   .--Obsolete------------------------------------------------------------.
#   |                 ___  _               _      _                        |
#   |                / _ \| |__  ___  ___ | | ___| |_ ___                  |
#   |               | | | | '_ \/ __|/ _ \| |/ _ \ __/ _ \                 |
#   |               | |_| | |_) \__ \ (_) | |  __/ ||  __/                 |
#   |                \___/|_.__/|___/\___/|_|\___|\__\___|                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | These Perf-O-Meters are not longer needed since thery are being      |
#   | handled by the new metrics.py module.                                |
#   '----------------------------------------------------------------------'
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

    return "%.1f s" % exectime, perfometer_linear(perc, color)
perfometers["check-mk"] = perfometer_check_mk


def perfometer_check_mk_cpu_loads(row, check_command, perf_data):
    color = { 0: "#68f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    load = float(perf_data[0][1])
    return "%.1f" % load, perfometer_logarithmic(load, 4, 2, color)

perfometers["check_mk-cpu.loads"] = perfometer_check_mk_cpu_loads
perfometers["check_mk-ucd_cpu_load"] = perfometer_check_mk_cpu_loads
perfometers["check_mk-statgrab_load"] = perfometer_check_mk_cpu_loads
perfometers["check_mk-hpux_cpu"] = perfometer_check_mk_cpu_loads
perfometers["check_mk-blade_bx_load"] = perfometer_check_mk_cpu_loads


def perfometer_check_mk_df(row, check_command, perf_data):
    varname, value, unit, warn, crit, minn, maxx = perf_data[0]

    hours_left = None
    for data in perf_data:
        if data[0] == "trend_hoursleft":
            hours_left = float(data[1])
            break

    perc_used = 100 * (float(value) / float(maxx))
    perc_free = 100 - float(perc_used)
    if hours_left or hours_left == 0:
        h = '<div class="stacked"><table><tr>'
        h += perfometer_td(perc_used, "#00ffc6")
        h += perfometer_td(perc_free, "white")
        h += "</tr></table><table><tr>"

        if hours_left == -1.0:
            h += perfometer_td(100, "#39c456")
            h += '</tr></table></div>'
            return "%0.1f%% / not growing" % (perc_used), h

        days_left = hours_left / 24
        if days_left > 30:
            color = "#39c456" # OK
        elif days_left < 7:
            color = "#d94747" # CRIT
        else:
            color = "#d7d139" # WARN

        half = math.log(30.0, 2) # value to be displayed at 50%
        pos = 50 + 10.0 * (math.log(days_left, 2) - half)
        if pos < 2:
            pos = 2
        if pos > 98:
            pos = 98
        h += perfometer_td(100 - pos, color)
        h += perfometer_td(pos, "white")
        h += '</tr></table></div>'
        if days_left > 365:
            days_left = " >365"
        else:
            days_left = "%0.1f" % days_left
        return "%0.1f%%/%s days left" % (perc_used, days_left), h
    else:
        h = '<table><tr>'
        h += perfometer_td(perc_used, "#00ffc6")
        h += perfometer_td(perc_free, "white")
        h += "</tr></table>"
        return "%0.2f %%" % perc_used, h

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
perfometers["check_mk-esx_vsphere_counters.ramdisk"] = perfometer_check_mk_df
perfometers["check_mk-hitachi_hnas_span"] = perfometer_check_mk_df
perfometers["check_mk-hitachi_hnas_volume"] = perfometer_check_mk_df
perfometers["check_mk-emcvnx_raidgroups.capacity"] = perfometer_check_mk_df
perfometers["check_mk-emcvnx_raidgroups.capacity_contiguous"] = perfometer_check_mk_df
perfometers["check_mk-ibm_svc_mdiskgrp"] = perfometer_check_mk_df
perfometers["check_mk-fast_lta_silent_cubes.capacity"] = perfometer_check_mk_df
perfometers["check_mk-fast_lta_volumes"] = perfometer_check_mk_df
perfometers["check_mk-libelle_business_shadow.archive_dir"] = perfometer_check_mk_df
perfometers["check_mk-netapp_api_volumes"] = perfometer_check_mk_df
perfometers["check_mk-df_zos"] = perfometer_check_mk_df

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

def perfometer_check_mk_cpu_threads(row, check_command, perf_data):
    color = { 0: "#a4f", 1: "#ff2", 2: "#f22", 3: "#fa2" }[row["service_state"]]
    return "%d" % int(perf_data[0][1]), perfometer_logarithmic(perf_data[0][1], 400, 2, color)

perfometers["check_mk-cpu.threads"] = perfometer_check_mk_cpu_threads

def perfometer_docsis_snr(row, check_command, perf_data):
    dbmv = float(perf_data[0][1])
    return "%.1f dB" % dbmv, perfometer_logarithmic(dbmv, 50, 2, "#ad6")

perfometers["check_mk-docsis_channels_upstream"] = perfometer_docsis_snr
