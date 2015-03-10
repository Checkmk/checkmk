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

# Metric definitions for Check_MK's checks

#   .--Units---------------------------------------------------------------.
#   |                        _   _       _ _                               |
#   |                       | | | |_ __ (_) |_ ___                         |
#   |                       | | | | '_ \| | __/ __|                        |
#   |                       | |_| | | | | | |_\__ \                        |
#   |                        \___/|_| |_|_|\__|___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definition of units of measurement.                                 |
#   '----------------------------------------------------------------------'

unit_info[""] = {
    "title"  : "",
    "symbol" : "",
    "render" : lambda v: "%.1f" % v,
}

unit_info["count"] = {
    "title"  : _("Count"),
    "symbol" : "",
    "render" : lambda v: "%d" % v,
}

# value ranges from 0.0 ... 100.0
unit_info["%"] = {
    "title"  : _("%"),
    "symbol" : _("%"),
    "render" : lambda v: "%s%%" % drop_dotzero(v),
}

# Similar as %, but value ranges from 0.0 ... 1.0
unit_info["ratio"] = {
    "title"  : _("Ratio"),
    "symbol" : _("%"),
    "render" : lambda v: "%s%%" % drop_dotzero(100.0 * v),
}

unit_info["s"] = {
    "title" : _("sec"),
    "symbol" : _("s"),
    "render" : age_human_readable,
}

unit_info["1/s"] = {
    "title" : _("per second"),
    "symbol" : _("/s"),
    "render" : lambda v: "%s%s" % (drop_dotzero(v), _("/s")),
}

unit_info["bytes"] = {
    "title"  : _("Bytes"),
    "symbol" : _("B"),
    "render" : bytes_human_readable,
}

unit_info["c"] = {
    "title"  : _("Degree Celsius"),
    "symbol" : _(u"°C"),
    "render" : lambda v: "%s %s" % (drop_dotzero(v), _(u"°C")),
}

unit_info["a"] = {
    "title"  : _("Electrical Current (Amperage)"),
    "symbol" : _("A"),
    "render" : lambda v: physical_precision(v, 3, _("A")),
}

unit_info["v"] = {
    "title"  : _("Electrical Tension (Voltage)"),
    "symbol" : _("V"),
    "render" : lambda v: physical_precision(v, 3, _("V")),
}

unit_info["w"] = {
    "title"  : _("Electrical Power"),
    "symbol" : _("W"),
    "render" : lambda v: physical_precision(v, 3, _("W")),
}

unit_info["va"] = {
    "title"  : _("Electrical Apparent Power"),
    "symbol" : _("VA"),
    "render" : lambda v: physical_precision(v, 3, _("VA")),
}

unit_info["wh"] = {
    "title"  : _("Electrical Energy"),
    "symbol" : _("Wh"),
    "render" : lambda v: physical_precision(v, 3, _("Wh")),
}

unit_info["dbm"] = {
    "title" : _("Decibel-milliwatts"),
    "symbol" : _("dBm"),
    "render" : lambda v: "%s %s" % (drop_dotzero(v), _("dBm")),
}

unit_info["db"] = {
    "title" : _("Decibel"),
    "symbol" : _("dB"),
    "render" : lambda v: physical_precision(v, 3, _("dB")),
}



#.
#   .--Metrics-------------------------------------------------------------.
#   |                   __  __      _        _                             |
#   |                  |  \/  | ___| |_ _ __(_) ___ ___                    |
#   |                  | |\/| |/ _ \ __| '__| |/ __/ __|                   |
#   |                  | |  | |  __/ |_| |  | | (__\__ \                   |
#   |                  |_|  |_|\___|\__|_|  |_|\___|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definitions of metrics                                              |
#   '----------------------------------------------------------------------'

metric_info["rta"] = {
    "title" : _("Round Trip Average"),
    "unit"  : "s",
    "color" : "#40a0b0",
}

metric_info["pl"] = {
    "title" : _("Packet loss"),
    "unit"  : "%",
    "color" : "#ffc030",
}

metric_info["hit_ratio"] = {
    "title" : _("Cache Hit Ratio"),
    "unit"  : "ratio",
    "color" : "#60c0c0",
}

metric_info["mem_used"] = {
    "title" : _("Used RAM"),
    "unit"  : "bytes",
    "color" : "#80ff40",
}

metric_info["mem_free"] = {
    "title" : _("Free RAM"),
    "unit"  : "bytes",
    "color" : "#ffffff",
}

metric_info["swap_used"] = {
    "title" : _("Used Swap space"),
    "unit"  : "bytes",
    "color" : "#008030",
}

metric_info["caches"] = {
    "title" : _("Memory used by caches"),
    "unit"  : "bytes",
    "color" : "#ffffff",
}

metric_info["swap_free"] = {
    "title" : _("Free Swap space"),
    "unit"  : "bytes",
    "color" : "#eeeeee",
}

metric_info["execution_time"] = {
    "title" : _("Execution time"),
    "unit"  : "s",
    "color" : "#22dd33",
}

metric_info["load1"] = {
    "title" : _("CPU load average of last minute"),
    "unit"  : "",
    "color" : "#6688ff",
}

metric_info["fs_used"] = {
    "title" : _("Used filesystem space"),
    "unit"  : "bytes",
    "color" : "#00ffc6",
}

metric_info["fs_provisioning"] = {
    "title" : _("Provisioned filesystem space"),
    "unit"  : "bytes",
    "color" : "#ff8000",
}


metric_info["temp"] = {
    "title" : _("Temperature"),
    "unit"  : "c",
    "color" : "#f0a040"
}

metric_info["ctxt"] = {
    "title" : _("Context switches"),
    "unit"  : "1/s",
    "color" : "#ddaa66",
}

metric_info["pgmajfault"] = {
    "title" : _("Major Page Faults"),
    "unit"  : "1/s",
    "color" : "#ddaa22",
}

metric_info["proc_creat"] = {
    "title" : _("Process creations"),
    "unit"  : "1/s",
    "color" : "#ddaa99",
}

metric_info["threads"] = {
    "title" : _("Number of threads"),
    "unit"  : "count",
    "color" : "#aa44ff",
}

metric_info["user"] = {
    "title" : _("User"),
    "help"  : _("Percentage of CPU time spent in user space"),
    "unit"  : "%",
    "color" : "#60f020",
}

metric_info["system"] = {
    "title" : _("System"),
    "help"  : _("Percentage of CPU time spent in kernel space"),
    "unit"  : "%",
    "color" : "#ff6000",
}

metric_info["util"] = {
    "title" : _("CPU Utilization"),
    "help"  : _("Percentage of CPU time used"),
    "unit"  : "%",
    "color" : "#60f020",
}

metric_info["io_wait"] = {
    "title" : _("IO-Wait"),
    "help"  : _("Percentage of CPU time spent waiting for IO"),
    "unit"  : "%",
    "color" : "#00b0c0",
}

metric_info["time_offset"] = {
    "title" : _("Time offset"),
    "unit"  : "s",
    "color" : "#9a52bf",
}

metric_info["input_signal_power_dbm"] = {
    "title" : _("Input Power"),
    "unit"  : "dbm",
    "color" : "#20c080",
}

metric_info["output_signal_power_dbm"] = {
    "title" : _("Output Power"),
    "unit"  : "dbm",
    "color" : "#2080c0",
}

metric_info["current"] = {
    "title" : _("Electrical Current"),
    "unit"  : "a",
    "color" : "#ffb030",
}

metric_info["voltage"] = {
    "title" : _("Electrical Voltage"),
    "unit"  : "v",
    "color" : "#ffc060",
}

metric_info["output_load"] = {
    "title" : _("Output Load"),
    "unit"  : "%",
    "color" : "#c080a0",
}

metric_info["power"] = {
    "title" : _("Electrical Power"),
    "unit"  : "w",
    "color" : "#8848c0",
}

metric_info["appower"] = {
    "title" : _("Electrical Apparent Power"),
    "unit"  : "va",
    "color" : "#aa68d80",
}

metric_info["energy"] = {
    "title" : _("Electrical Energy"),
    "unit"  : "wh",
    "color" : "#aa80b0",
}

metric_info["output_load"] = {
    "title" : _("Output load"),
    "unit"  : "%",
    "color" : "#c83880",
}

metric_info["voltage_percent"] = {
    "title" : _("Electrical Tension in % of normal value"),
    "unit"  : "%",
    "color" : "#ffc020",
}

metric_info["humidity"] = {
    "title" : _("Relative Humidity"),
    "unit"  : "%",
    "color" : "#90b0b0",
}

metric_info["requests_per_second"] = {
    "title" : _("Requests per second"),
    "unit"  : "1/s",
    "color" : "#4080a0",
}

metric_info["busy_workers"] = {
    "title" : _("Busy Workers"),
    "unit"  : "count",
    "color" : "#a080b0",
}

metric_info["signal_noise"] = {
    "title" : _("Signal/Noise Ratio"),
    "unit"  : "db",
    "color" : "#aadd66",
}

metric_info["codewords_corrected"] = {
    "title" : _("Corrected Codewords"),
    "unit"  : "ratio",
    "color" : "#ff8040",
}

metric_info["codewords_uncorrectable"] = {
    "title" : _("Uncorrectable Codewords"),
    "unit"  : "ratio",
    "color" : "#ff4020",
}


#.
#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  How various checks' performance data translate into the known       |
#   |  metrics                                                             |
#   '----------------------------------------------------------------------'

check_metrics["check-mk-ping"]                                  = {}
check_metrics["check-mk"]                                       = {}

check_metrics["check_mk-cpu.loads"]                             = {}
check_metrics["check_mk-ucd_cpu_load"]                          = {}
check_metrics["check_mk-statgrab_load"]                         = {}
check_metrics["check_mk-hpux_cpu"]                              = {}
check_metrics["check_mk-blade_bx_load"]                         = {}

check_metrics["check_mk-cpu.threads"]                           = {}

check_metrics["check_mk-mem.linux"]                             = {}
check_metrics["check_mk-aix_memory"]                            = { "ramused" : { "name" : "mem_used", "scale": MB }, "swapused" : { "name" : "swap_used", "scale": MB }}
check_metrics["check_mk-mem.win"]                               = { "memory" : { "name" : "mem_used", "scale" : MB }, "pagefile" : { "name" : "pagefile_used", "scale" : MB }}

check_metrics["check_mk-df"]                                    = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-vms_df"]                                = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-vms_diskstat.df"]                       = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_disk"]                                     = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-df_netapp"]                             = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-df_netapp32"]                           = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-zfsget"]                                = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-hr_fs"]                                 = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-oracle_asm_diskgroup"]                  = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-mysql_capacity"]                        = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-esx_vsphere_counters.ramdisk"]          = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-hitachi_hnas_span"]                     = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-hitachi_hnas_volume"]                   = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-emcvnx_raidgroups.capacity"]            = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-emcvnx_raidgroups.capacity_contiguous"] = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-ibm_svc_mdiskgrp"]                      = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-fast_lta_silent_cubes.capacity"]        = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-fast_lta_volumes"]                      = { 0: { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-libelle_business_shadow.archive_dir"]   = { 0: { "name": "fs_used", "scale" : MB } }

check_metrics["check_mk-apc_symmetra_ext_temp"]                 = {}
check_metrics["check_mk-adva_fsp_temp"]                         = {}
check_metrics["check_mk-akcp_daisy_temp"]                       = {}
check_metrics["check_mk-akcp_exp_temp"]                         = {}
check_metrics["check_mk-akcp_sensor_temp"]                      = {}
check_metrics["check_mk-allnet_ip_sensoric.temp"]               = {}
check_metrics["check_mk-apc_inrow_temperature"]                 = {}
check_metrics["check_mk-apc_symmetra_temp"]                     = {}
check_metrics["check_mk-arris_cmts_temp"]                       = {}
check_metrics["check_mk-bintec_sensors.temp"]                   = {}
check_metrics["check_mk-brocade.temp"]                          = {}
check_metrics["check_mk-brocade_mlx_temp"]                      = {}
check_metrics["check_mk-carel_sensors"]                         = {}
check_metrics["check_mk-casa_cpu_temp"]                         = {}
check_metrics["check_mk-cisco_temp_perf"]                       = {}
check_metrics["check_mk-cisco_temp_sensor"]                     = {}
check_metrics["check_mk-climaveneta_temp"]                      = {}
check_metrics["check_mk-cmciii.temp"]                           = {}
check_metrics["check_mk-cmctc.temp"]                            = {}
check_metrics["check_mk-cmctc_lcp.temp"]                        = {}
check_metrics["check_mk-dell_chassis_temp"]                     = {}
check_metrics["check_mk-dell_om_sensors"]                       = {}
check_metrics["check_mk-dell_poweredge_temp"]                   = {}
check_metrics["check_mk-decru_temps"]                           = {}
check_metrics["check_mk-emc_datadomain_temps"]                  = {}
check_metrics["check_mk-enterasys_temp"]                        = {}
check_metrics["check_mk-f5_bigip_chassis_temp"]                 = {}
check_metrics["check_mk-f5_bigip_cpu_temp"]                     = {}
check_metrics["check_mk-fsc_temp"]                              = {}
check_metrics["check_mk-hitachi_hnas_temp"]                     = {}
check_metrics["check_mk-hp_proliant_temp"]                      = {}
check_metrics["check_mk-hwg_temp"]                              = {}
check_metrics["check_mk-ibm_svc_enclosurestats.temp"]           = {}
check_metrics["check_mk-innovaphone_temp"]                      = {}
check_metrics["check_mk-juniper_screenos_temp"]                 = {}
check_metrics["check_mk-kentix_temp"]                           = {}
check_metrics["check_mk-knuerr_rms_temp"]                       = {}
check_metrics["check_mk-lnx_thermal"]                           = {}
check_metrics["check_mk-netapp_api_temp"]                       = {}
check_metrics["check_mk-netscaler_health.temp"]                 = {}
check_metrics["check_mk-nvidia.temp"]                           = {}
check_metrics["check_mk-ups_bat_temp"]                          = {}
check_metrics["check_mk-qlogic_sanbox.temp"]                    = {}
check_metrics["check_mk-rms200_temp"]                           = {}
check_metrics["check_mk-sensatronics_temp"]                     = {}
check_metrics["check_mk-smart.temp"]                            = {}
check_metrics["check_mk-viprinet_temp"]                         = {}
check_metrics["check_mk-wagner_titanus_topsense.temp"]          = {}
check_metrics["check_mk-cmciii.phase"]                          = {}
check_metrics["check_mk-ucs_bladecenter_fans.temp"]             = {}
check_metrics["check_mk-ucs_bladecenter_psu.chassis_temp"]      = {}

check_metrics["check_mk-kernel"]                                = { "processes" : { "name" : "proc_creat", } }

check_metrics["check_mk-hr_cpu"]                                = {}
check_metrics["check_mk-kernel.util"]                           = { "wait" : { "name" : "io_wait" } }
check_metrics["check_mk-lparstat_aix.cpu_util"]                 = { "wait" : { "name" : "io_wait" } }
check_metrics["check_mk-ucd_cpu_util"]                          = { "wait" : { "name" : "io_wait" } }
check_metrics["check_mk-vms_cpu"]                               = { "wait" : { "name" : "io_wait" } }
check_metrics["check_mk-vms_sys.util"]                          = { "wait" : { "name" : "io_wait" } }

check_metrics["check_mk-mbg_lantime_state"]                     = { "offset" : { "name" : "time_offset", "scale" : 0.000001 }} # convert us -> sec
check_metrics["check_mk-mbg_lantime_ng_state"]                  = { "offset" : { "name" : "time_offset", "scale" : 0.000001 }} # convert us -> sec
check_metrics["check_mk-systemtime"]                            = { "offset" : { "name" : "time_offset" }}

check_metrics["check_mk-adva_fsp_if"]                           = { "output_power" : { "name" : "output_signal_power_dbm" },
                                                                    "input_power" : { "name" : "input_signal_power_dbm" }}

check_metrics["check_mk-allnet_ip_sensoric.tension"]            = { "tension" : { "name" : "voltage_percent" }}
check_metrics["check_mk-adva_fsp_current"]                      = {}

check_metrics["check_mk-akcp_exp_humidity"]                     = {}
check_metrics["check_mk-apc_humidity"]                          = {}
check_metrics["check_mk-hwg_humidity"]                          = {}


check_metrics["check_mk-apache_status"]                         = { "ReqPerSec" : { "name" : "requests_per_second" }, "BusyWorkers" : { "name" : "busy_workers" }}

check_metrics["check_mk-bintec_sensors.voltage"]                = {}
check_metrics["check_mk-hp_blade_psu"]                          = { "output" : { "name" : "power" }}
check_metrics["check_mk-apc_rackpdu_power"]                     = { "amperage" : { "name" : "current" }}
check_metrics["check_mk-apc_ats_output"]                        = { "volt" : { "name" : "voltage" }, "watt" : { "name" : "power"}, "ampere": { "name": "current"}, "load_perc" : { "name": "output_load" }}
check_metrics["check_mk-raritan_pdu_inlet"]                     = {}
check_metrics["check_mk-raritan_pdu_inlet_summary"]             = {}
check_metrics["check_mk-ups_socomec_outphase"]                  = {}
check_metrics["check_mk-ucs_bladecenter_psu.switch_power"]      = {}

check_metrics["check_mk-bluecoat_sensors"]                      = {}

check_metrics["check_mk-zfs_arc_cache"]                         = { "hit_ratio" : { "scale" : 0.01 }}
check_metrics["check_mk-docsis_channels_upstream"]              = {}

#.
#   .--Perf-O-Meters-------------------------------------------------------.
#   |  ____            __        ___        __  __      _                  |
#   | |  _ \ ___ _ __ / _|      / _ \      |  \/  | ___| |_ ___ _ __ ___   |
#   | | |_) / _ \ '__| |_ _____| | | |_____| |\/| |/ _ \ __/ _ \ '__/ __|  |
#   | |  __/  __/ |  |  _|_____| |_| |_____| |  | |  __/ ||  __/ |  \__ \  |
#   | |_|   \___|_|  |_|        \___/      |_|  |_|\___|\__\___|_|  |___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definition of Perf-O-Meters                                         |
#   '----------------------------------------------------------------------'

# Types of Perf-O-Meters:
# linear      -> multiple values added from left to right
# logarithmic -> one value in a logarithmic scale
# dual        -> two Perf-O-Meters next to each other, the first one from right to left
# stacked     -> two Perf-O-Meters of type linear, logarithmic or dual, stack vertically
# The label of dual and stacked is taken from the definition of the contained Perf-O-Meters

perfometer_info.append(("logarithmic",  ( "rta", 0.1, 4)))
perfometer_info.append(("linear",      ( ["execution_time"], 90.0, None)))
perfometer_info.append(("logarithmic",  ( "load1",         4.0, 2.0)))
perfometer_info.append(("logarithmic",  ( "temp",         40.0, 1.2)))
perfometer_info.append(("logarithmic",  ( "ctxt",       1000.0, 2.0)))
perfometer_info.append(("logarithmic",  ( "pgmajfault", 1000.0, 2.0)))
perfometer_info.append(("logarithmic",  ( "proc_creat", 1000.0, 2.0)))
perfometer_info.append(("logarithmic",  ( "threads",     400.0, 2.0)))
perfometer_info.append(("linear",      ( [ "user", "system", "io_wait" ],                               100.0,       None)))
perfometer_info.append(("linear",      ( [ "util", ],                                                   100.0,       None)))

# Filesystem check with over-provisioning
perfometer_info.append({
    "type"      : "linear",
    "condition" : "fs_provisioning(%),100,>",
    "segments"  : [
        "fs_used(%)",
        "100,fs_used(%),-#FFFFFF",
        "fs_provisioning(%),100.0,-#ffc030",
    ],
    "total"     : "fs_provisioning(%)",
    "label"     : ( "fs_used(%)", "%" ),
})

# Filesystem check with provisioning, but not over-provisioning
perfometer_info.append({
    "type"      : "linear",
    "condition" : "fs_provisioning(%),100,<=",
    "segments"  : [
        "fs_used(%)",
        "fs_provisioning(%),fs_used(%),-#ffc030",
    ],
    "total"     : "100",
    "label"     : ( "fs_used(%)", "%" ),
})

# perfometer_info.append(("linear",      ( [ "fs_used(%)", "fs_provisioning(%),100.0,-", ], 200.0, None))) # ("fs_used(%)", "%"))))
# perfometer_info.append(("linear",      ( [ "fs_used(%)", ], "fs_provisioning(%)", ("fs_used(%)", "%"))))
# perfometer_info.append(("linear",      ( [ "fs_used(%)", "100.0,fs_used(%),-", ], "fs_provisioning(%)", "fs_used(%)")))

perfometer_info.append(("stacked", [
  ("linear",      ( [ "fs_used(%)" ],     100.0, None)),
  ("logarithmic", ( "fs_provisioning(%)", 100.0, 1.2)),
]))

# and without
perfometer_info.append(("linear",      ( [ "fs_used(%)" ],                                              100.0,       None)))

perfometer_info.append(("linear",      ( [ "mem_used", "swap_used", "caches", "mem_free", "swap_free" ], None,
("mem_total,mem_used,+,swap_used,/", "ratio"))))
perfometer_info.append(("linear",      ( [ "mem_used" ],                                                "mem_total", None)))
perfometer_info.append(("linear",      ( [ "mem_used(%)" ],                                              100.0, None)))
perfometer_info.append(("logarithmic",  ( "time_offset",  1.0, 10.0)))

perfometer_info.append(("dual", [
   ( "logarithmic", ( "input_signal_power_dbm", 4, 2)),
   ( "logarithmic", ( "output_signal_power_dbm", 4, 2)),
]))

perfometer_info.append(("linear",      ( [ "output_load" ], 100.0, None)))
perfometer_info.append(("logarithmic", ( "power", 1000, 2)))
perfometer_info.append(("logarithmic", ( "current", 10, 4)))
perfometer_info.append(("logarithmic", ( "voltage", 220.0, 2)))
perfometer_info.append(("linear",      ( [ "voltage_percent" ], 100.0, None)))
perfometer_info.append(("linear",      ( [ "humidity" ], 100.0, None)))

perfometer_info.append(("stacked",    [
  ( "logarithmic", ( "requests_per_second", 10, 5)),
  ( "logarithmic", ( "busy_workers",        10, 2))]))

perfometer_info.append(("linear",      ( [ "hit_ratio" ], 1.0, None)))
perfometer_info.append(("stacked",  [
   ("logarithmic",  ( "signal_noise", 50.0, 2.0)),
   ("linear",       ( [ "codewords_corrected", "codewords_uncorrectable" ], 1.0, None)),
]))
perfometer_info.append(("logarithmic",  ( "signal_noise", 50.0, 2.0))) # Fallback if no codewords are available

#.
#   .--Graphs--------------------------------------------------------------.
#   |                    ____                 _                            |
#   |                   / ___|_ __ __ _ _ __ | |__  ___                    |
#   |                  | |  _| '__/ _` | '_ \| '_ \/ __|                   |
#   |                  | |_| | | | (_| | |_) | | | \__ \                   |
#   |                   \____|_|  \__,_| .__/|_| |_|___/                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Definitions of time series graphs                                   |
#   '----------------------------------------------------------------------'
graph_info.append({
    # "title"          : _("Das ist der Titel"),       # Wenn fehlt, dann nimmt er den Titel der ersten Metrik
    # "vertical_label" : _("Das hier kommt vertikal"), # Wenn fehlt, dann nimmt er die Unit der ersten Metrik
    "metrics" : [
        ( "fs_used", "area" ),
    ]
})

graph_info.append({
    "title"   : _("CPU utilization"),
    "metrics" : [
        ( "user",                           "area"  ),
        ( "system",                         "stack" ),
        ( "io_wait",                        "stack" ),
        ( "user,system,io_wait,+,+#004080", "line", _("Total") ),
    ],
    "mirror_legend" : True,
    "range" : (0, 100),
})

graph_info.append({
    "metrics" : [
        ( "time_offset", "area" ),
    ]
})
