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

# TODO: Move fundamental units like "" to main file.

unit_info[""] = {
    "title"  : "",
    "symbol" : "",
    "render" : lambda v: "%.1f" % v,
}

unit_info["count"] = {
    "title"    : _("Count"),
    "symbol"   : "",
    "render"   : lambda v: "%d" % v,
    "stepping" : "integer", # for vertical graph labels
}

# value ranges from 0.0 ... 100.0
unit_info["%"] = {
    "title"  : _("%"),
    "symbol" : _("%"),
    "render" : lambda v: percent_human_redable(v, 3),
}

# Similar as %, but value ranges from 0.0 ... 1.0
unit_info["ratio"] = {
    "title"  : _("%"),
    "symbol" : _("%"),
    "render_scale" : 100.0, # Scale by this before rendering if "render" not being used
    "render" : lambda v: percent_human_redable(v, 3),
}

unit_info["s"] = {
    "title"    : _("sec"),
    "symbol"   : _("s"),
    "render"   : age_human_readable,
    "stepping" : "time", # for vertical graph labels
}

unit_info["1/s"] = {
    "title" : _("per second"),
    "symbol" : _("/s"),
    "render" : lambda v: "%s%s" % (drop_dotzero(v), _("/s")),
}

unit_info["bytes"] = {
    "title"    : _("Bytes"),
    "symbol"   : _("B"),
    "render"   : bytes_human_readable,
    "stepping" : "binary", # for vertical graph labels
}

unit_info["bytes/s"] = {
    "title"    : _("Bytes per second"),
    "symbol"   : _("B/s"),
    "render"   : lambda v: bytes_human_readable(v) + _("/s"),
    "stepping" : "binary", # for vertical graph labels
}

unit_info["bits/s"] = {
    "title"    : _("Bits per second"),
    "symbol"   : _("bits/s"),
    "render"   : lambda v: physical_precision(v, 3, _("bit/s")),
}

# Output in bytes/days, value is in bytes/s
unit_info["bytes/d"] = {
    "title"    : _("Bytes per day"),
    "symbol"   : _("B/d"),
    "render"   : lambda v: bytes_human_readable(v * 86400.0) + _("/d"),
    "stepping" : "binary", # for vertical graph labels
}

unit_info["c"] = {
    "title"  : _("Degree Celsius"),
    "symbol" : u"°C",
    "render" : lambda v: "%s %s" % (drop_dotzero(v), u"°C"),
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

# Title are always lower case - except the first character!

metric_info["rta"] = {
    "title" : _("Round trip average"),
    "unit"  : "s",
    "color" : "#40a0b0",
}

metric_info["pl"] = {
    "title" : _("Packet loss"),
    "unit"  : "%",
    "color" : "#ffc030",
}

metric_info["response_time"] = {
    "title" : _("Response time"),
    "unit"  : "s",
    "color" : "#40a0b0",
}

metric_info["uptime"] = {
    "title" : _("Uptime"),
    "unit"  : "s",
    "color" : "#80f000",
}

metric_info["runtime"] = {
    "title" : _("Process Runtime"),
    "unit"  : "s",
    "color" : "#80f000",
}

metric_info["hit_ratio"] = {
    "title" : _("Cache hit ratio"),
    "unit"  : "ratio",
    "color" : "#60c0c0",
}

metric_info["database_size"] = {
    "title" : _("Database size"),
    "unit"  : "bytes",
    "color" : "#00868B",
}

metric_info["mem_total"] = {
    "title" : _("RAM installed"),
    "color": "#f0f0f0",
    "unit" : "bytes",
}

metric_info["mem_free"] = {
    "title" : _("Free RAM"),
    "color" : "#ffffff",
    "unit"  : "bytes",
}

metric_info["mem_used"] = {
    "color": "#80ff40",
    "title" : _("RAM used"),
    "unit" : "bytes",
}

metric_info["swap_total"] = {
    "title" : _("Swap installed"),
    "color": "#e0e0e0",
    "unit" : "bytes",
}

metric_info["swap_free"] = {
    "title" : _("Free swap space"),
    "unit"  : "bytes",
    "color" : "#eeeeee",
}

metric_info["swap_used"] = {
    "title" : _("Swap used"),
    "color": "#408f20",
    "unit" : "bytes",
}

metric_info["swap_cached"] = {
    "title" : _("Swap cached"),
    "color": "#5bebc9",
    "unit" : "bytes",
}

metric_info["caches"] = {
    "title" : _("Memory used by caches"),
    "unit"  : "bytes",
    "color" : "#ffffff",
}


metric_info["mem_lnx_cached"] = {
    "title" : _("File contents"),
    "color": "#91cceb",
    "unit" : "bytes",
}

metric_info["mem_lnx_buffers"] = {
    "title" : _("Filesystem structure"),
    "color": "#5bb9eb",
    "unit" : "bytes",
}

metric_info["mem_lnx_slab"] = {
    "title" : _("Slab (Various smaller caches)"),
    "color": "#af91eb",
    "unit" : "bytes",
}

metric_info["mem_lnx_active_anon"] = {
    "title" : _("Active   (anonymous)"),
    "color": "#ff4040",
    "unit" : "bytes",
}

metric_info["mem_lnx_active_file"] = {
    "title" : _("Active   (files)"),
    "color": "#ff8080",
    "unit" : "bytes",
}

metric_info["mem_lnx_inactive_anon"] = {
    "title" : _("Inactive (anonymous)"),
    "color": "#377cab",
    "unit" : "bytes",
}

metric_info["mem_lnx_inactive_file"] = {
    "title" : _("Inactive (files)"),
    "color": "#4eb0f2",
    "unit" : "bytes",
}

metric_info["mem_lnx_active"] = {
    "title" : _("Active"),
    "color": "#ff4040",
    "unit" : "bytes",
}

metric_info["mem_lnx_inactive"] = {
    "title" : _("Inactive"),
    "color": "#4040ff",
    "unit" : "bytes",
}

metric_info["mem_lnx_dirty"] = {
    "title" : _("Dirty disk blocks"),
    "color": "#f2904e",
    "unit" : "bytes",
}

metric_info["mem_lnx_writeback"] = {
    "title" : _("Currently being written"),
    "color": "#f2df40",
    "unit" : "bytes",
}

metric_info["mem_lnx_nfs_unstable"] = {
    "title" : _("Modified NFS data"),
    "color": "#c6f24e",
    "unit" : "bytes",
}

metric_info["mem_lnx_bounce"] = {
    "title" : _("Bounce buffers"),
    "color": "#4ef26c",
    "unit" : "bytes",
}

metric_info["mem_lnx_writeback_tmp"] = {
    "title" : _("Dirty FUSE data"),
    "color": "#4eeaf2",
    "unit" : "bytes",
}

metric_info["mem_lnx_total_total"] = {
    "title" : _("Total virtual memory"),
    "color": "#f0f0f0",
    "unit" : "bytes",
}

metric_info["mem_lnx_committed_as"] = {
    "title" : _("Committed memory"),
    "color": "#40a080",
    "unit" : "bytes",
}

metric_info["mem_lnx_commit_limit"] = {
    "title" : _("Commit limit"),
    "color": "#e0e0e0",
    "unit" : "bytes",
}

metric_info["mem_lnx_shmem"] = {
    "title" : _("Shared memory"),
    "color": "#bf9111",
    "unit" : "bytes",
}

metric_info["mem_lnx_kernel_stack"] = {
    "title" : _("Kernel stack"),
    "color": "#7192ad",
    "unit" : "bytes",
}

metric_info["mem_lnx_page_tables"] = {
    "title" : _("Page tables"),
    "color": "#71ad9f",
    "unit" : "bytes",
}

metric_info["mem_lnx_mlocked"] = {
    "title" : _("Locked mmap() data"),
    "color": "#a671ad",
    "unit" : "bytes",
}

metric_info["mem_lnx_huge_pages_total"] = {
    "title" : _("Total"),
    "color": "#f0f0f0",
    "unit" : "bytes",
}

metric_info["mem_lnx_huge_pages_free"] = {
    "title" : _("Free"),
    "color": "#f0a0f0",
    "unit" : "bytes",
}

metric_info["mem_lnx_huge_pages_rsvd"] = {
    "title" : _("Reserved part of Free"),
    "color": "#40f0f0",
    "unit" : "bytes",
}

metric_info["mem_lnx_huge_pages_surp"] = {
    "title" : _("Surplus"),
    "color": "#90f0b0",
    "unit" : "bytes",
}

metric_info["mem_lnx_vmalloc_total"] = {
    "title" : _("Total address space"),
    "color": "#f0f0f0",
    "unit" : "bytes",
}

metric_info["mem_lnx_vmalloc_used"] = {
    "title" : _("Allocated space"),
    "color": "#aaf76f",
    "unit" : "bytes",
}

metric_info["mem_lnx_vmalloc_chunk"] = {
    "title" : _("Largest free chunk"),
    "color": "#c6f7e9",
    "unit" : "bytes",
}

metric_info["execution_time"] = {
    "title" : _("Execution time"),
    "unit"  : "s",
    "color" : "#22dd33",
}

metric_info["load1"] = {
    "title" : _("CPU load average of last minute"),
    "unit"  : "",
    "color" : "#60c0e0",
}

metric_info["load5"] = {
    "title" : _("CPU load average of last 5 minutes"),
    "unit"  : "",
    "color" : "#428399",
}

metric_info["load15"] = {
    "title" : _("CPU load average of last 15 minutes"),
    "unit"  : "",
    "color" : "#2c5766",
}

metric_info["context_switches"] = {
    "title" : _("Context switches"),
    "unit"  : "1/s",
    "color" : "#80ff20",
}

metric_info["major_page_faults"] = {
    "title" : _("Major page faults"),
    "unit"  : "1/s",
    "color" : "#20ff80",
}

metric_info["process_creations"] = {
    "title" : _("Process creations"),
    "unit"  : "1/s",
    "color" : "#ff8020",
}

metric_info["threads"] = {
    "title" : _("Number of running threads"),
    "unit"  : "count",
    "color" : "#8040f0",
}

metric_info["fs_used"] = {
    "title" : _("Used filesystem space"),
    "unit"  : "bytes",
    "color" : "#00ffc6",
}

metric_info["inodes_used"] = {
    "title" : _("Used inodes"),
    "unit"  : "count",
    "color" : "#a0608f",
}

metric_info["fs_size"] = {
    "title" : _("Filesystem size"),
    "unit"  : "bytes",
    "color" : "#006040",
}

metric_info["fs_growth"] = {
    "title" : _("Filesystem growth"),
    "unit"  : "bytes/d",
    "color" : "#29cfaa",
}

metric_info["fs_trend"] = {
    "title" : _("Trend of filesystem growth"),
    "unit"  : "bytes/d",
    "color" : "#808080",
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

metric_info["threads"] = {
    "title" : _("Number of threads"),
    "unit"  : "count",
    "color" : "#9a77ee",
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
    "title" : _("CPU utilization"),
    "help"  : _("Percentage of CPU time used"),
    "unit"  : "%",
    "color" : "#60f020",
}

metric_info["io_wait"] = {
    "title" : _("IO-wait"),
    "help"  : _("Percentage of CPU time spent waiting for IO"),
    "unit"  : "%",
    "color" : "#00b0c0",
}

metric_info["time_offset"] = {
    "title" : _("Time offset"),
    "unit"  : "s",
    "color" : "#9a52bf",
}

metric_info["connection_time"] = {
    "title" : _("Connection time"),
    "unit"  : "s",
    "color" : "#94b65a",
}

metric_info["input_signal_power_dbm"] = {
    "title" : _("Input power"),
    "unit"  : "dbm",
    "color" : "#20c080",
}

metric_info["output_signal_power_dbm"] = {
    "title" : _("Output power"),
    "unit"  : "dbm",
    "color" : "#2080c0",
}

metric_info["tablespace_wasted"] = {
    "title" : _("Tablespace wasted"),
    "unit"  : "bytes",
    "color" : "#a02020",
}

metric_info["indexspace_wasted"] = {
    "title" : _("Indexspace wasted"),
    "unit"  : "bytes",
    "color" : "#20a080",
}

metric_info["current"] = {
    "title" : _("Electrical current"),
    "unit"  : "a",
    "color" : "#ffb030",
}

metric_info["voltage"] = {
    "title" : _("Electrical voltage"),
    "unit"  : "v",
    "color" : "#ffc060",
}

metric_info["power"] = {
    "title" : _("Electrical power"),
    "unit"  : "w",
    "color" : "#8848c0",
}

metric_info["appower"] = {
    "title" : _("Electrical apparent power"),
    "unit"  : "va",
    "color" : "#aa68d80",
}

metric_info["energy"] = {
    "title" : _("Electrical energy"),
    "unit"  : "wh",
    "color" : "#aa80b0",
}

metric_info["output_load"] = {
    "title" : _("Output load"),
    "unit"  : "%",
    "color" : "#c83880",
}

metric_info["voltage_percent"] = {
    "title" : _("Electrical tension in % of normal value"),
    "unit"  : "%",
    "color" : "#ffc020",
}

metric_info["humidity"] = {
    "title" : _("Relative humidity"),
    "unit"  : "%",
    "color" : "#90b0b0",
}

metric_info["requests_per_second"] = {
    "title" : _("Requests per second"),
    "unit"  : "1/s",
    "color" : "#4080a0",
}

metric_info["busy_workers"] = {
    "title" : _("Busy workers"),
    "unit"  : "count",
    "color" : "#a080b0",
}

metric_info["connections"] = {
    "title" : _("Connections"),
    "unit"  : "count",
    "color" : "#a080b0",
}

metric_info["signal_noise"] = {
    "title" : _("Signal/Noise ratio"),
    "unit"  : "db",
    "color" : "#aadd66",
}

metric_info["codewords_corrected"] = {
    "title" : _("Corrected codewords"),
    "unit"  : "ratio",
    "color" : "#ff8040",
}

metric_info["codewords_uncorrectable"] = {
    "title" : _("Uncorrectable codewords"),
    "unit"  : "ratio",
    "color" : "#ff4020",
}

metric_info["total_sessions"] = {
    "title" : _("Total sessions"),
    "unit"  : "count",
    "color" : "#94b65a",
}

metric_info["running_sessions"] = {
    "title" : _("Running sessions"),
    "unit"  : "count",
    "color" : "#999b94",
}

metric_info["shared_locks"] = {
    "title" : _("Shared locks"),
    "unit"  : "count",
    "color" : "#92ec89",
}

metric_info["exclusive_locks"] = {
    "title" : _("Exclusive locks"),
    "unit"  : "count",
    "color" : "#ca5706",
}

metric_info["disk_read_throughput"] = {
    "title" : _("Read throughput"),
    "unit"  : "bytes/s",
    "color" : "#40c080",
}

metric_info["disk_write_throughput"] = {
    "title" : _("Write throughput"),
    "unit"  : "bytes/s",
    "color" : "#4080c0",
}

metric_info["disk_read_ios"] = {
    "title" : _("Read operations"),
    "unit"  : "1/s",
    "color" : "#60e0a0",
}

metric_info["disk_write_ios"] = {
    "title" : _("Write operations"),
    "unit"  : "1/s",
    "color" : "#60a0e0",
}

metric_info["disk_average_read_wait"] = {
    "title" : _("Read wait Time"),
    "unit"  : "s",
    "color" : "#20e8c0",
}

metric_info["disk_average_write_wait"] = {
    "title" : _("Write wait time"),
    "unit"  : "s",
    "color" : "#20c0e8",
}

metric_info["disk_average_wait"] = {
    "title" : _("Request wait time"),
    "unit"  : "s",
    "color" : "#4488cc",
}

metric_info["disk_average_read_request_size"] = {
    "title" : _("Average read request size"),
    "unit"  : "bytes",
    "color" : "#409c58",
}

metric_info["disk_average_write_request_size"] = {
    "title" : _("Average write request size"),
    "unit"  : "bytes",
    "color" : "#40589c",
}

metric_info["disk_average_request_size"] = {
    "title" : _("Average request size"),
    "unit"  : "bytes",
    "color" : "#4488cc",
}

metric_info["disk_latency"] = {
    "title" : _("Average disk latency"),
    "unit"  : "s",
    "color" : "#c04080",
}

metric_info["disk_queue_length"] = {
    "title" : _("Disk IO-queue length"),
    "unit"  : "",
    "color" : "#7060b0",
}

metric_info["disk_utilization"] = {
    "title" : _("Disk utilization"),
    "unit"  : "ratio",
    "color" : "#a05830",
}

metric_info["xda_hitratio"] = {
    "title" : _("XDA hitratio"),
    "unit"  : "%",
    "color" : "#0ae86d",
}

metric_info["data_hitratio"] = {
    "title" : _("Data hitratio"),
    "unit"  : "%",
    "color" : "#2828de",
}

metric_info["index_hitratio"] = {
    "title" : _("Index hitratio"),
    "unit"  : "%",
    "color" : "#dc359f",
}

metric_info["total_hitratio"] = {
    "title" : _("Total hitratio"),
    "unit"  : "%",
    "color" : "#2e282c",
}

metric_info["deadlocks"] = {
    "title" : _("Deadlocks"),
    "unit"  : "1/s",
    "color" : "#dc359f",
}

metric_info["lockwaits"] = {
    "title" : _("Waitlocks"),
    "unit"  : "1/s",
    "color" : "#2e282c",
}

metric_info["sort_overflow"] = {
    "title" : _("Sort overflow"),
    "unit"  : "%",
    "color" : "#e72121",
}

metric_info["tablespace_size"] = {
    "title" : _("Tablespace size"),
    "unit"  : "bytes",
    "color" : "#092507",
}

metric_info["tablespace_used"] = {
    "title" : _("Tablespace used"),
    "unit"  : "bytes",
    "color" : "#e59d12",
}

metric_info["tablespace_max_size"] = {
    "title" : _("Tablespace max size"),
    "unit"  : "bytes",
    "color" : "#172121",
}

metric_info["hours_operation"] = {
    "title" : _("Hours of operation"),
    "unit"  : "s",
    "color" : "#94b65a",
}

metric_info["hours_since_service"] = {
    "title" : _("Hours since service"),
    "unit"  : "s",
    "color" : "#94b65a",
}

metric_info["execution_time"] = {
    "title" : _("Total execution time"),
    "unit"  : "s",
    "color" : "#d080af",
}

metric_info["user_time"] = {
    "title" : _("CPU time in user space"),
    "unit"  : "s",
    "color" : "#60f020",
}

metric_info["system_time"] = {
    "title" : _("CPU time in system space"),
    "unit"  : "s",
    "color" : "#ff6000",
}

metric_info["children_user_time"] = {
    "title" : _("Child time in user space"),
    "unit"  : "s",
    "color" : "#aef090",
}

metric_info["children_system_time"] = {
    "title" : _("Child time in system space"),
    "unit"  : "s",
    "color" : "#ffb080",
}

metric_info["printer_queue"] = {
    "title" : _("Printer queue length"),
    "unit"  : "count",
    "color" : "#a63df2",
}

metric_info["if_in_octets"] = {
    "title" : _("Input Octets"),
    "unit"  : "bytes/s",
    "color" : "#00e060",
}

metric_info["if_out_octets"] = {
    "title" : _("Output Octets"),
    "unit"  : "bytes/s",
    "color" : "#0080e0",
}

metric_info["if_in_discards"] = {
    "title" : _("Input Discards"),
    "unit"  : "1/s",
    "color" : "#ff8000",
}

metric_info["if_in_errors"] = {
    "title" : _("Input Errors"),
    "unit"  : "1/s",
    "color" : "#ff0000",
}

metric_info["if_out_discards"] = {
    "title" : _("Output Dicards"),
    "unit"  : "1/s",
    "color" : "#ff8080",
}

metric_info["if_out_errors"] = {
    "title" : _("Output Errors"),
    "unit"  : "1/s",
    "color" : "#ff0080",
}

metric_info["if_in_unicast"] = {
    "title" : _("Input unicast packets"),
    "unit"  : "1/s",
    "color" : "#00ffc0",
}

metric_info["if_in_non_unicast"] = {
    "title" : _("Input non-unicast packets"),
    "unit"  : "1/s",
    "color" : "#00c080",
}

metric_info["if_out_unicast"] = {
    "title" : _("Output unicast packets"),
    "unit"  : "1/s",
    "color" : "#00c0ff",
}

metric_info["if_out_non_unicast"] = {
    "title" : _("Output non-unicast packets"),
    "unit"  : "1/s",
    "color" : "#0080c0",
}

metric_info["tcp_established"] = {
    "title" : _("State %s") % "ESTABLISHED",
    "unit"  : "count",
    "color" : "#00f040",
}

metric_info["tcp_syn_sent"] = {
    "title" : _("State %s") % "SYN_SENT",
    "unit"  : "count",
    "color" : "#a00000",
}

metric_info["tcp_syn_recv"] = {
    "title" : _("State %s") % "SYN_RECV",
    "unit"  : "count",
    "color" : "#ff4000",
}

metric_info["tcp_last_ack"] = {
    "title" : _("State %s") % "LAST_ACK",
    "unit"  : "count",
    "color" : "#c060ff",
}

metric_info["tcp_close_wait"] = {
    "title" : _("State %s") % "CLOSE_WAIT",
    "unit"  : "count",
    "color" : "#f000f0",
}

metric_info["tcp_time_wait"] = {
    "title" : _("State %s") % "TIME_WAIT",
    "unit"  : "count",
    "color" : "#00b0b0",
}

metric_info["tcp_closed"] = {
    "title" : _("State %s") % "CLOSED",
    "unit"  : "count",
    "color" : "#ffc000",
}

metric_info["tcp_closing"] = {
    "title" : _("State %s") % "CLOSING",
    "unit"  : "count",
    "color" : "#ffc080",
}

metric_info["tcp_fin_wait1"] = {
    "title" : _("State %s") % "FIN_WAIT1",
    "unit"  : "count",
    "color" : "#cccccc",
}

metric_info["tcp_fin_wait2"] = {
    "title" : _("State %s") % "FIN_WAIT2",
    "unit"  : "count",
    "color" : "#888888",
}

metric_info["tcp_bound"] = {
    "title" : _("State %s") % "BOUND",
    "unit"  : "count",
    "color" : "#4060a0",
}

metric_info["host_check_rate"] = {
    "title" : _("Host check rate"),
    "unit"  : "1/s",
    "color" : "#884422",
}

metric_info["service_check_rate"] = {
    "title" : _("Service check rate"),
    "unit"  : "1/s",
    "color" : "#ffbb66",
}

metric_info["livestatus_connect_rate"] = {
    "title" : _("Livestatus connects"),
    "unit"  : "1/s",
    "color" : "#556677",
}

metric_info["livestatus_request_rate"] = {
    "title" : _("Livestatus requests"),
    "unit"  : "1/s",
    "color" : "#bbccdd",
}

metric_info["log_message_rate"] = {
    "title" : _("Log messages"),
    "unit"  : "1/s",
    "color" : "#aa44cc",
}

metric_info["normal_updates"] = {
    "title" : _("Pending normal updates"),
    "unit"  : "count",
    "color" : "#c08030",
}

metric_info["security_updates"] = {
    "title" : _("Pending security updates"),
    "unit"  : "count",
    "color" : "#ff0030",
}

metric_info["used_dhcp_leases"] = {
    "title" : _("Used DHCP leases"),
    "unit"  : "count",
    "color" : "#60bbbb",
}

metric_info["registered_phones"] = {
    "title" : _("Registered phones"),
    "unit"  : "count",
    "color" : "#60bbbb",
}

metric_info["messages"] = {
    "title" : _("Messages"),
    "unit"  : "count",
    "color" : "#aa44cc",
}

metric_info["call_legs"] = { 
    "title" : _("Call legs"),
    "unit"  : "count",
    "color" : "#60bbbb",
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

check_metrics["check-mk"]                                       = {}
check_metrics["check-mk-ping"]                                  = {}
check_metrics["check-mk"]                                       = {}

check_metrics["check_mk_active-tcp"]                            = { "time" : { "name": "response_time" } }
check_metrics["check-mk-host-tcp"]                              = { "time" : { "name": "response_time" } }

check_metrics["check_mk-uptime"]                                = {}
check_metrics["check_mk-esx_vsphere_counters.uptime"]           = {}
check_metrics["check_mk-fritz.uptime"]                          = {}
check_metrics["check_mk-jolokia_metrics.uptime"]                = {}
check_metrics["check_mk-snmp_uptime"]                           = {}

check_metrics["check_mk-cpu.loads"]                             = {}
check_metrics["check_mk-ucd_cpu_load"]                          = {}
check_metrics["check_mk-statgrab_load"]                         = {}
check_metrics["check_mk-hpux_cpu"]                              = {}
check_metrics["check_mk-blade_bx_load"]                         = {}

check_metrics["check_mk-kernel"]                                = {
    "ctxt"       : { "name": "context_switches" },
    "pgmajfault" : { "name": "major_page_faults" },
    "processes"  : { "name": "process_creations" },
}

check_metrics["check_mk-cpu.threads"]                           = {}

check_metrics["check_mk-aix_sap_processlist"]                   = {}
check_metrics["check_mk-aix_memory"]                            = { "ramused" : { "name" : "mem_used", "scale": MB }, "swapused" : { "name" : "swap_used", "scale": MB }}
check_metrics["check_mk-mem.win"]                               = { "memory" : { "name" : "mem_used", "scale" : MB }, "pagefile" : { "name" : "pagefile_used", "scale" : MB }}

check_metrics["check_mk-mem.linux"]                             = {
    "cached"           : { "name" : "mem_lnx_cached", },
    "buffers"          : { "name" : "mem_lnx_buffers", },
    "slab"             : { "name" : "mem_lnx_slab", },
    "active_anon"      : { "name" : "mem_lnx_active_anon", },
    "active_file"      : { "name" : "mem_lnx_active_file", },
    "inactive_anon"    : { "name" : "mem_lnx_inactive_anon", },
    "inactive_file"    : { "name" : "mem_lnx_inactive_file", },
    "active"           : { "name" : "mem_lnx_active", },
    "inactive"         : { "name" : "mem_lnx_inactive", },
    "dirty"            : { "name" : "mem_lnx_dirty", },
    "writeback"        : { "name" : "mem_lnx_writeback", },
    "nfs_unstable"     : { "name" : "mem_lnx_nfs_unstable", },
    "bounce"           : { "name" : "mem_lnx_bounce", },
    "writeback_tmp"    : { "name" : "mem_lnx_writeback_tmp", },
    "total_total"      : { "name" : "mem_lnx_total_total", },
    "committed_as"     : { "name" : "mem_lnx_committed_as", },
    "commit_limit"     : { "name" : "mem_lnx_commit_limit", },
    "shmem"            : { "name" : "mem_lnx_shmem", },
    "kernel_stack"     : { "name" : "mem_lnx_kernel_stack", },
    "page_tables"      : { "name" : "mem_lnx_page_tables", },
    "mlocked"          : { "name" : "mem_lnx_mlocked", },
    "huge_pages_total" : { "name" : "mem_lnx_huge_pages_total", },
    "huge_pages_free"  : { "name" : "mem_lnx_huge_pages_free", },
    "huge_pages_rsvd"  : { "name" : "mem_lnx_huge_pages_rsvd", },
    "huge_pages_surp"  : { "name" : "mem_lnx_huge_pages_surp", },
    "vmalloc_total"    : { "name" : "mem_lnx_vmalloc_total", },
    "vmalloc_used"     : { "name" : "mem_lnx_vmalloc_used", },
    "vmalloc_chunk"    : { "name" : "mem_lnx_vmalloc_chunk", },
}

check_metrics["check_mk-tcp_conn_stats"] = {
    "SYN_SENT"    : { "name": "tcp_syn_sent" },
    "SYN_RECV"    : { "name": "tcp_syn_recv" },
    "ESTABLISHED" : { "name": "tcp_established" },
    "TIME_WAIT"   : { "name": "tcp_time_wait" },
    "LAST_ACK"    : { "name": "tcp_last_ack" },
    "CLOSE_WAIT"  : { "name": "tcp_close_wait" },
    "CLOSED"      : { "name": "tcp_closed" },
    "CLOSING"     : { "name": "tcp_closing" },
    "FIN_WAIT1"   : { "name": "tcp_fin_wait1" },
    "FIN_WAIT2"   : { "name": "tcp_fin_wait2" },
    "BOUND"       : { "name": "tcp_bound" },
}

df_translation = {
    "~(?!fs_size|growth|trend|fs_provisioning).*"   : { "name"  : "fs_used", "scale" : MB },
    "fs_size" : { "scale" : MB },
    "growth"  : { "name"  : "fs_growth", "scale" : MB / 86400.0 },
    "trend"   : { "name"  : "fs_trend", "scale" : MB / 86400.0 },
}
check_metrics["check_mk-df"]                                    = df_translation
check_metrics["check_mk-vms_df"]                                = df_translation
check_metrics["check_mk-vms_diskstat.df"]                       = df_translation
check_metrics["check_disk"]                                     = df_translation
check_metrics["check_mk-df_netapp"]                             = df_translation
check_metrics["check_mk-df_netapp32"]                           = df_translation
check_metrics["check_mk-zfsget"]                                = df_translation
check_metrics["check_mk-hr_fs"]                                 = df_translation
check_metrics["check_mk-oracle_asm_diskgroup"]                  = df_translation
check_metrics["check_mk-esx_vsphere_counters.ramdisk"]          = df_translation
check_metrics["check_mk-hitachi_hnas_span"]                     = df_translation
check_metrics["check_mk-hitachi_hnas_volume"]                   = df_translation
check_metrics["check_mk-emcvnx_raidgroups.capacity"]            = df_translation
check_metrics["check_mk-emcvnx_raidgroups.capacity_contiguous"] = df_translation
check_metrics["check_mk-ibm_svc_mdiskgrp"]                      = df_translation
check_metrics["check_mk-fast_lta_silent_cubes.capacity"]        = df_translation
check_metrics["check_mk-fast_lta_volumes"]                      = df_translation
check_metrics["check_mk-libelle_business_shadow.archive_dir"]   = df_translation

# in=0;;;0; inucast=0;;;; innucast=0;;;; indisc=0;;;; inerr=0;0.01;0.1;; out=0;;;0; outucast=0;;;; outnucast=0;;;; outdisc=0;;;; outerr=0;0.01;0.1;; outqlen=0;;;0;
if_translation = {
    "in"        : { "name": "if_in_octets" },
    "out"       : { "name": "if_out_octets" },
    "indisc"    : { "name": "if_in_discards" },
    "inerr"     : { "name": "if_in_errors" },
    "outdisc"   : { "name": "if_out_discards" },
    "outerr"    : { "name": "if_out_errors" },
    "inucast"   : { "name": "if_in_unicast" },
    "innucast"  : { "name": "if_in_non_unicast" },
    "outucast"  : { "name": "if_out_unicast" },
    "outnucast" : { "name": "if_out_non_unicast" },
}
check_metrics["check_mk-esx_vsphere_counters"] = if_translation
check_metrics["check_mk-fritz"]                = if_translation
check_metrics["check_mk-hitachi_hnas_fc_if"]   = if_translation
check_metrics["check_mk-if64"]                 = if_translation
check_metrics["check_mk-if64_tplink"]          = if_translation
check_metrics["check_mk-if_lancom"]            = if_translation
check_metrics["check_mk-if"]                   = if_translation
check_metrics["check_mk-lnx_if"]               = if_translation
check_metrics["check_mk-mcdata_fcport"]        = if_translation
check_metrics["check_mk-netapp_api_if"]        = if_translation
check_metrics["check_mk-statgrab_net"]         = if_translation
check_metrics["check_mk-ucs_bladecenter_if"]   = if_translation
check_metrics["check_mk-vms_if"]               = if_translation
check_metrics["check_mk-winperf_if"]           = if_translation


check_metrics["check_mk-diskstat"]                              = {}

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
check_metrics["check_mk-icom_repeater.temp"]                    = {}
check_metrics["check_mk-ucs_bladecenter_psu.chassis_temp"]      = {}

check_metrics["check_mk-mysql_capacity"]                        = {}

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
check_metrics["check_mk-bluenet_meter"]                         = {}

check_metrics["check_mk-bluecoat_sensors"]                      = {}

check_metrics["check_mk-zfs_arc_cache"]                         = { "hit_ratio" : { "scale" : 0.01 }}
check_metrics["check_mk-docsis_channels_upstream"]              = {}

check_metrics["check_mk-postgres_bloat"]                        = {}
check_metrics["check_mk-postgres_connections"]                  = {}
check_metrics["check_mk-postgres_locks"]                        = {}
check_metrics["check_mk-postgres_conn_time"]                    = {}
check_metrics["check_mk-postgres_sessions"]                     = { "total": {"name": "total_sessions"}, "running": {"name": "running_sessions"} }

check_metrics["check_mk-db2_bp_hitratios"]                      = {}
check_metrics["check_mk-db2_connections"]                       = {}
check_metrics["check_mk-db2_counters"]                          = {}
check_metrics["check_mk-db2_logsize"]                           = { "~[_/]": { "name": "fs_used", "scale" : MB } }
check_metrics["check_mk-db2_sort_overflow"]                     = {}
check_metrics["check_mk-db2_tablespaces"]                       = {}
check_metrics["check_mk-siemens_plc.temp"]                      = {}
check_metrics["check_mk-siemens_plc.hours"]                     = {}

check_metrics["check_mk-cups_queues"]                           = { "jobs" : { "name" : "printer_queue" } }

check_metrics["check_mk-livestatus_status"] = {
    "host_checks"    : { "name" : "host_check_rate" },
    "service_checks" : { "name" : "service_check_rate" },
    "connections"    : { "name" : "livestatus_connect_rate" },
    "requests"       : { "name" : "livestatus_request_rate" },
    "log_messages"   : { "name" : "log_message_rate" },
}

check_metrics["check_mk-apt"] = {}
check_metrics["check_mk-icom_repeater.ps_volt"] = {}
check_metrics["check_mk-icom_repeater.pll_volt"] = {}
check_metrics["check_mk-isc_dhcpd"] = {}
check_metrics["check_mk-cisco_srst_phones"] = {}
check_metrics["check_mk-cisco_srst_call_legs"] = {}

check_metrics["check_mk-logwatch.ec"] = {}
check_metrics["check_mk-logwatch.ec_single"] = {}


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

perfometer_info.append({
    "type"     : "linear",
    "segments" : [ "execution_time" ],
    "total"    : 90.0,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "uptime",
    "half_value" : 2592000.0,
    "exponent"   : 2,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "runtime",
    "half_value" : 864000.0,
    "exponent"   : 2,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "response_time",
    "half_value" : 10,
    "exponent"   : 4,
})


perfometer_info.append(("logarithmic",  ( "rta", 0.1, 4)))
perfometer_info.append(("linear",       ( ["execution_time"], 90.0, None)))
perfometer_info.append(("logarithmic",  ( "load1",         4.0, 2.0)))
perfometer_info.append(("logarithmic",  ( "temp",         40.0, 1.2)))
perfometer_info.append(("logarithmic",  ( "context_switches",       1000.0, 2.0)))
perfometer_info.append(("logarithmic",  ( "major_page_faults", 1000.0, 2.0)))
perfometer_info.append(("logarithmic",  ( "process_creations", 1000.0, 2.0)))
perfometer_info.append(("logarithmic",  ( "threads",     400.0, 2.0)))
perfometer_info.append(("linear",       ( [ "user", "system", "io_wait" ],                               100.0,       None)))
perfometer_info.append(("linear",       ( [ "util", ],                                                   100.0,       None)))
perfometer_info.append(("logarithmic",  ( "database_size", GB, 5.0 )))

# Filesystem check with over-provisioning
perfometer_info.append({
    "type"      : "linear",
    "condition" : "fs_provisioning(%),100,>",
    "segments"  : [
        "fs_used(%)",
        "100,fs_used(%),-#e3fff9",
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
        "100,fs_provisioning(%),fs_used(%),-,-#e3fff9",
    ],
    "total"     : 100,
    "label"     : ( "fs_used(%)", "%" ),
})

# Filesystem without over-provisioning
perfometer_info.append({
    "type"      : "linear",
    "segments"  : [
        "fs_used(%)",
        "100.0,fs_used(%),-#e3fff9",
    ],
    "total"     : 100,
    "label"     : ( "fs_used(%)", "%" ),
})


perfometer_info.append(("linear",      ( [ "mem_used", "swap_used", "caches", "mem_free", "swap_free" ], None,
("mem_total,mem_used,+,swap_used,/", "ratio"))))
perfometer_info.append(("linear",      ( [ "mem_used" ],                                                "mem_total", None)))
perfometer_info.append(("linear",      ( [ "mem_used(%)" ],                                              100.0, None)))
perfometer_info.append(("logarithmic",  ( "time_offset",  1.0, 10.0)))

perfometer_info.append(("stacked", [
   ( "logarithmic", ( "tablespace_wasted", 1000000, 2)),
   ( "logarithmic", ( "indexspace_wasted", 1000000, 2)),
]))

perfometer_info.append(("linear",      ( [ "running_sessions" ],                                        "total_sessions", None)))
perfometer_info.append(("linear",      ( [ "shared_locks", "exclusive_locks" ],                         None, None)))

perfometer_info.append(("linear",      ( [ "connections" ], 100, None)))
perfometer_info.append(("logarithmic", ( "connection_time", 0.2, 2)))

perfometer_info.append(("dual", [
   ( "logarithmic", ( "input_signal_power_dbm", 4, 2)),
   ( "logarithmic", ( "output_signal_power_dbm", 4, 2)),
]))


perfometer_info.append(("dual", [
   ( "logarithmic", ( "deadlocks", 50, 2)),
   ( "logarithmic", ( "lockwaits", 50, 2)),
]))


perfometer_info.append({
    "type"      : "linear",
    "segments"  : [
        "sort_overflow",
    ],
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [
        "tablespace_used",
    ],
    "total"     : "tablespace_size",
})

perfometer_info.append(("stacked", [
("dual", [ {"type": "linear", "label": None, "segments": [ "total_hitratio" ], "total": 100},
           {"type": "linear", "label": None, "segments": [ "data_hitratio" ],  "total": 100}]),
("dual", [ {"type": "linear", "label": None, "segments": [ "index_hitratio" ], "total": 100},
           {"type": "linear", "label": None, "segments": [ "xda_hitratio" ],   "total": 100}])
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

perfometer_info.append(("dual", [
   ( "logarithmic", ( "disk_read_throughput", 5000000, 10)),
   ( "logarithmic", ( "disk_write_throughput", 5000000, 10)),
]))

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "printer_queue",
    "half_value" : 10,
    "exponent"   : 2,
})

perfometer_info.append(("linear",      ( [ "used_dhcp_leases" ], "used_dhcp_leases:max", None)))

perfometer_info.append(("stacked", [
  ( "logarithmic", ( "host_check_rate",     50, 5)),
  ( "logarithmic", ( "service_check_rate", 200, 5)),
]))

perfometer_info.append(("stacked", [
  ( "logarithmic", ( "normal_updates",   10, 2)),
  ( "logarithmic", ( "security_updates", 10, 2)),
]))

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "registered_phones",
    "half_value" : 50,
    "exponent"   : 3,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "call_legs",
    "half_value" : 10,
    "exponent"   : 2,
})


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

def define_generic_graph(metric_name):
    graph_info.append({
        "metrics" : [
            ( metric_name, "area" ),
        ],
        "scalars" : [
            metric_name + ":warn",
            metric_name + ":crit",
        ]
    })

define_generic_graph("context_switches")
define_generic_graph("major_page_faults")
define_generic_graph("process_creations")
define_generic_graph("threads")
define_generic_graph("runtime")
define_generic_graph("execution_time")
define_generic_graph("response_time")
define_generic_graph("uptime")
define_generic_graph("temp")
define_generic_graph("time_offset")


graph_info.append({
    "title" : _("Used CPU Time"),
    "metrics" : [
        ( "user_time",            "area" ),
        ( "children_user_time",   "stack" ),
        ( "system_time",          "stack" ),
        ( "children_system_time", "stack" ),
    ],
})


graph_info.append({
    "title"   : _("CPU Load - %(load1:max@count) CPU Cores"),
    "metrics" : [
        ( "load1", "area" ),
        ( "load15", "line" ),
    ],
    "scalars" : [
        "load1:warn",
        "load1:crit",
    ]
})


graph_info.append({
    "metrics" : [
        ( "fs_used", "area" ),
        ( "fs_size,fs_used,-#e3fff9", "stack", _("Free space") ),
        ( "fs_size", "line" ),
    ],
    "scalars" : [
        "fs_used:warn",
        "fs_used:crit",
    ],
    "range" : (0, "fs_used:max"),
})


graph_info.append({
    "title" : _("Growing / Shrinking"),
    "metrics" : [
       ( "fs_growth.max,0,MAX",             "area",  _("Growth"), ),
       ( "fs_growth.min,0,MIN,-1,*#299dcf", "-area", _("Shrinkage") ),
    ],
})

graph_info.append({
    "metrics" : [
       ( "fs_trend", "line" ),
    ],
    "range" : (0, 0),
})

define_generic_graph("inodes_used")


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
    "title"   : _("Wasted space of tables and indexes"),
    "metrics" : [
        ( "tablespace_wasted", "area" ),
        ( "indexspace_wasted", "stack" ),
    ],
    "legend_scale" : MB,
    "legend_precision" : 2,
})

graph_info.append({
    "title": _("Time to connect"),
    "metrics" : [
        ( "connection_time", "area" ),
    ],
    "legend_scale" : m,
})

graph_info.append({
    "title": _("Number of connections"),
    "metrics" : [
        ( "connections", "line" ),
    ],
})

graph_info.append({
    "title": _("Number of total and running sessions"),
    "metrics" : [
        ( "running_sessions", "line" ),
        ( "total_sessions",   "line" ),
    ],
    "legend_precision" : 0
})

graph_info.append({
    "title": _("Number of shared and exclusive locks"),
    "metrics" : [
        ( "shared_locks",    "area" ),
        ( "exclusive_locks", "stack" ),
    ],
    "legend_precision" : 0
})

# diskstat checks

graph_info.append({
    "metrics" : [
        ( "disk_utilization",  "area" ),
    ],
    "range" : (0, 1),
})

graph_info.append({
    "title" : _("Disk Throughput"),
    "metrics" : [
        ( "disk_read_throughput",  "area" ),
        ( "disk_write_throughput", "-area" ),
    ],
    "legend_scale" : MB,
})

graph_info.append({
    "title" : _("Disk I/O Operations"),
    "metrics" : [
        ( "disk_read_ios",  "area" ),
        ( "disk_write_ios", "-area" ),
    ],
})

graph_info.append({
    "title" : _("Average request size"),
    "metrics" : [
        ( "disk_average_read_request_size",  "area" ),
        ( "disk_average_write_request_size", "-area" ),
    ],
    "legend_scale" : KB,
})


graph_info.append({
    "title" : _("Average end to end wait time"),
    "metrics" : [
        ( "disk_average_read_wait",  "area" ),
        ( "disk_average_write_wait", "-area" ),
    ],
})

graph_info.append({
    "metrics" : [
        ( "disk_latency",  "area" ),
    ],
})

graph_info.append({
    "metrics" : [
        ( "disk_queue_length",  "area" ),
    ],
})

graph_info.append({
    "metrics" : [
        ( "database_size",  "area" ),
    ],
    "legend_scale" : MB,
})

# TODO: Warum ist hier überall line? Default ist Area.
# Kann man die hit ratios nicht schön stacken? Ist
# nicht total die Summe der anderen?

graph_info.append({
    "title" : _("Bufferpool Hitratios"),
    "metrics" : [
        ( "total_hitratio", "line" ),
        ( "data_hitratio",  "line" ),
        ( "index_hitratio", "line" ),
        ( "xda_hitratio",   "line" ),
    ],
})

# TODO: Warum sind die in einem Graphen? Kann man
# die irgendwie addieren?
graph_info.append({
    "metrics" : [
        ( "deadlocks",  "line" ),
        ( "lockwaits",  "line" ),
    ],
})

graph_info.append({
    "metrics" : [
        ( "sort_overflow",  "area" ),
    ],
})

# TODO: Warum auch hier line? Sollte mit
# areas arbeiten. Habe das mal umgestellt, aber noch
# nicht getestet.
graph_info.append({
    "metrics" : [
        ( "tablespace_used",  "area" ),
        ( "tablespace_size",  "area" ),
    ],
})

graph_info.append({
    "metrics" : [
         ( "printer_queue", "area" )
    ],
    "range" : (0, 10),
})

# Networking

graph_info.append({
    "title" : _("Bandwidth"),
    "metrics" : [
        ( "if_in_octets,8,*@bits/s",   "area", _("Input bandwidth") ),
        ( "if_out_octets,8,*@bits/s",  "-area", _("Output bandwidth") ),
    ],
})

# TODO: show this graph instead of Bandwidth if this is configured
# in the check's parameters. But is this really a good solution?
# We could use a condition on if_in_octets:min. But if this value
# is missing then evaluating the condition will fail. Solution
# could be using 0 for bits and 1 for octets and making sure that
# this value is not used anywhere.
# graph_info.append({
#     "title" : _("Octets"),
#     "metrics" : [
#         ( "if_in_octets",      "area" ),
#         ( "if_out_octets",     "-area" ),
#     ],
# })

graph_info.append({
    "title" : _("Packets"),
    "metrics" : [
        ( "if_in_unicast",      "area" ),
        ( "if_in_non_unicast",  "stack" ),
        ( "if_out_unicast",     "-area" ),
        ( "if_out_non_unicast", "-stack" ),
    ],
})

graph_info.append({
    "title" : _("Errors"),
    "metrics" : [
        ( "if_in_errors",    "area" ),
        ( "if_in_discards",  "stack" ),
        ( "if_out_errors",   "-area" ),
        ( "if_out_discards", "-stack" ),
    ],
})

# Linux memory graphs. They are a lot...

graph_info.append({
    "title" : _("RAM + Swap overview"),
    "metrics" : [
        ("mem_total",  "area"),
        ("swap_total", "stack"),
        ("mem_used",   "area"),
        ("swap_used",  "stack"),
    ],
})

graph_info.append({
    "title" : _("Swap"),
    "metrics" : [
        ("swap_total",  "area"),
        ("swap_used",   "area"),
        ("swap_cached", "stack"),
    ],
})

graph_info.append({
    "title" : _("Caches"),
    "metrics" : [
        ("mem_lnx_slab",    "stack"),
        ("swap_cached",     "stack"),
        ("mem_lnx_buffers", "stack"),
        ("mem_lnx_cached",  "stack"),
    ],
})

graph_info.append({
    "title" : _("Active and Inactive Memory"),
    "metrics" : [
        ("mem_lnx_inactive_anon", "stack"),
        ("mem_lnx_inactive_file", "stack"),
        ("mem_lnx_active_anon",   "stack"),
        ("mem_lnx_active_file",   "stack"),
    ],
})


# TODO: Show this graph only, if the previous graph
# is not possible. This cannot be done with a condition,
# since we currently cannot state a condition on non-existing
# metrics.
graph_info.append({
    "title" : _("Active and Inactive Memory"),
    "metrics" : [
        ("mem_lnx_active", "area"),
        ("mem_lnx_inactive", "area"),
    ],
    "not_if_have" : [ "mem_lnx_active_anon" ],
})

graph_info.append({
    "title" : _("Filesystem Writeback"),
    "metrics" : [
        ("mem_lnx_dirty", "area"),
        ("mem_lnx_writeback", "stack"),
        ("mem_lnx_nfs_unstable", "stack"),
        ("mem_lnx_bounce", "stack"),
        ("mem_lnx_writeback_tmp", "stack"),
    ],
})

graph_info.append({
    "title" : _("Memory committing"),
    "metrics" : [
        ("mem_lnx_total_total", "area"),
        ("mem_lnx_committed_as", "area"),
        ("mem_lnx_commit_limit", "stack"),
    ],
})

graph_info.append({
    "title" : _("Shared memory"),
    "metrics" : [
        ("mem_lnx_shmem", "area"),
    ],
})

graph_info.append({
    "title" : _("Memory that cannot be swapped out"),
    "metrics" : [
        ("mem_lnx_kernel_stack", "area"),
        ("mem_lnx_page_tables", "stack"),
        ("mem_lnx_mlocked", "stack"),
    ],
})

graph_info.append({
    "title" : _("Huge Pages"),
    "metrics" : [
        ("mem_lnx_huge_pages_total", "area"),
        ("mem_lnx_huge_pages_free", "area"),
        ("mem_lnx_huge_pages_rsvd", "area"),
        ("mem_lnx_huge_pages_surp", "line"),
    ],
})

graph_info.append({
    "title" : _("VMalloc Address Space"),
    "metrics" : [
        ("mem_lnx_vmalloc_total", "area"),
        ("mem_lnx_vmalloc_used", "area"),
        ("mem_lnx_vmalloc_chunk", "stack"),
    ],
})

graph_info.append({
    "title" : _("TCP Connection States"),
    "metrics" : [
       ( "tcp_syn_sent",    "stack"),
       ( "tcp_syn_recv",    "stack"),
       ( "tcp_established", "stack"),
       ( "tcp_time_wait",   "stack"),
       ( "tcp_last_ack",    "stack"),
       ( "tcp_close_wait",  "stack"),
       ( "tcp_closed",      "stack"),
       ( "tcp_closing",     "stack"),
       ( "tcp_fin_wait1",   "stack"),
       ( "tcp_fin_wait2",   "stack"),
       ( "tcp_bound",       "stack"),
    ],
    "omit_zero_metrics" : True,
})

graph_info.append({
    "title" : _("Host and Service Checks"),
    "metrics" : [
        ( "host_check_rate",    "stack" ),
        ( "service_check_rate", "stack" ),
    ],
})

graph_info.append({
    "title" : _("Livestatus Connects and Requests"),
    "metrics" : [
        ( "livestatus_request_rate", "area" ),
        ( "livestatus_connect_rate", "area" ),
    ],
})

graph_info.append({
    "title" : _("Livestatus Requests per Connection"),
    "metrics" : [
        ( "livestatus_request_rate,livestatus_connect_rate,/#88aa33", "area",
          _("Averate requests per connection")),
    ],
})

graph_info.append({
    "title" : _("Pending updates"),
    "metrics" : [
        ( "normal_updates",    "stack" ),
        ( "security_updates",  "stack" ),
    ],
})

graph_info.append({
    "title" : _("Used DHCP Leases"),
    "metrics" : [
        ( "used_dhcp_leases",    "area" ),
    ],
    "range" : (0, "used_dhcp_leases:max"),
    "scalars" : [
        "used_dhcp_leases:warn",
        "used_dhcp_leases:crit",
        ("used_dhcp_leases:max#000000", _("Total number of leases")),
    ]
})

graph_info.append({
    "metrics" : [
        ( "registered_phones", "area" ),
    ],
})

graph_info.append({
    "metrics" : [
        ( "messages", "area" ),
    ],
})

graph_info.append({
    "metrics" : [
        ( "call_legs", "area" )
    ],
})
