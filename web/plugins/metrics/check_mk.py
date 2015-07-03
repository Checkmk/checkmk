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

# TODO Graphingsystem:
# - Default-Template: Wenn im Graph kein "range" angegeben ist, aber
# in der Unit eine "range"-Angabe ist, dann soll diese genommen werden.
# "%" und "ratio". Und dann sämtliche Schablonen, die nur wegen Range
# 0..100 da sind, wieder durch generic ersetzen.

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

unit_info["hz"] = {
    "title"  : _("Hz"),
    "symbol" : _("Hz"),
    "render" : lambda v : physical_precision(v, 3, _("Hz")),
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

# 'Percent obscuration per meter'-Obscuration for any atmospheric phenomenon, e.g. smoke, dust, snow
unit_info["%/m"] = {
    "title"     : _("Percent Per Meter"),
    "symbol"    : _("%/m"),
    "render"    : lambda v: percent_human_redable(v, 3) + _("/m"),
}

unit_info["bar"] = {
    "title"     : _("Bar"),
    "symbol"    : _("bar"),
    "render"    : lambda v: physical_precision(v, 4, _("bar")),
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

# Colors:
#
#                   red
#  magenta                       orange
#            11 12 13 14 15 16
#         46                   21
#         45                   22
#   blue  44                   23  yellow
#         43                   24
#         42                   25
#         41                   26
#            36 35 34 33 32 31
#     cyan                       yellow-green
#                  green
#
# Special colors:
# 51  gray
# 52  brown 1
# 53  brown 2
#
# For a new metric_info you have to choose a color. No more hex-codes are needed!
# Instead you can choose a number of the above color ring and a letter 'a' or 'b
# where 'a' represents the basic color and 'b' is a nuance/shading of the basic color.
# Both number and letter must be declared!
#
# Example:
# "color" : "23/a" (basic color yellow)
# "color" : "23/b" (nuance of color yellow)

metric_info["rta"] = {
    "title" : _("Round trip average"),
    "unit"  : "s",
    "color" : "#40a0b0",
}

metric_info["rtmin"] = {
    "title" : _("Round trip minimum"),
    "unit"  : "s",
    "color" : "42/a",
}

metric_info["rtmax"] = {
    "title" : _("Round trip maximum"),
    "unit"  : "s",
    "color" : "42/b",
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

metric_info["lifetime_remaining"] = {
    "title" : _("Lifetime remaining"),
    "unit"  : "s",
    "color" : "#80f000",
}

metric_info["cache_hit_ratio"] = {
    "title" : _("Cache hit ratio"),
    "unit"  : "%",
    "color" : "#60c0c0",
}

metric_info["zfs_l2_hit_ratio"] = {
    "title" : _("L2 cache hit ratio"),
    "unit"  : "%",
    "color" : "46/a",
}

metric_info["prefetch_data_hit_ratio"] = {
    "title" : _("Prefetch data hit ratio"),
    "unit"  : "%",
    "color" : "41/b",
}

metric_info["prefetch_metadata_hit_ratio"] = {
    "title" : _("Prefetch metadata hit ratio"),
    "unit"  : "%",
    "color" : "43/a",
}

metric_info["zfs_metadata_used"] = {
    "title" : _("Used meta data"),
    "unit"  : "bytes",
    "color" : "31/a",
}

metric_info["zfs_metadata_max"] = {
    "title" : _("Maxmimum of meta data"),
    "unit"  : "bytes",
    "color" : "33/a",
}

metric_info["zfs_metadata_limit"] = {
    "title" : _("Limit of meta data"),
    "unit"  : "bytes",
    "color" : "36/a",
}

metric_info["zfs_l2_size"] = {
    "title" : _("L2 cache size"),
    "unit"  : "bytes",
    "color" : "31/a",
}

# database, tablespace

metric_info["database_size"] = {
    "title" : _("Database size"),
    "unit"  : "bytes",
    "color" : "16/a",
}

metric_info["data_size"] = {
    "title" : _("Data size"),
    "unit"  : "bytes",
    "color" : "25/a",
}

metric_info["unallocated_size"] = {
    "title" : _("Unallocated space"),
    "help"  : _("Space in the database that has not been reserved for database objects"),
    "unit"  : "bytes",
    "color" : "34/a",
}

metric_info["reserved_size"] = {
    "title" : _("Reserved space"),
    "help"  : _("Total amount of space allocated by objects in the database"),
    "unit"  : "bytes",
    "color" : "41/a",
}

metric_info["indexes_size"] = {
    "title" : _("Index space"),
    "unit"  : "bytes",
    "color" : "31/a",
}

metric_info["unused_size"] = {
    "title" : _("Unused space"),
    "help"  : _("Total amount of space reserved for objects in the database, but not yed used"),
    "unit"  : "bytes",
    "color" : "46/a",
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
    "title" : _("Tablespace maximum size"),
    "unit"  : "bytes",
    "color" : "#172121",
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

metric_info["mem_perm_used"] = {
    "color": "#80ff40",
    "title" : _("Perm used"),
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
    "color" : "51/a",
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
    "title" : _("Active (anonymous)"),
    "color": "#ff4040",
    "unit" : "bytes",
}

metric_info["mem_lnx_active_file"] = {
    "title" : _("Active (files)"),
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

metric_info["mem_lnx_mapped"] = {
    "title" : _("Mapped data"),
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

metric_info["load1"] = {
    "title" : _("CPU load average of last minute"),
    "unit"  : "",
    "color" : "34/c",
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

metric_info["process_virtual_size"] = {
    "title" : _("Virtual size"),
    "unit"  : "bytes",
    "color" : "16/a",
}

metric_info["process_resident_size"] = {
    "title" : _("Resident size"),
    "unit"  : "bytes",
    "color" : "14/a",
}

metric_info["mem_heap"] = {
    "title" : _("Heap memory usage"),
    "unit"  : "bytes",
    "color" : "23/a",
}

metric_info["mem_heap_committed"] = {
    "title" : _("Heap memory committed"),
    "unit"  : "bytes",
    "color" : "23/b",
}

metric_info["mem_nonheap"] = {
    "title" : _("Non-heap memory usage"),
    "unit"  : "bytes",
    "color" : "16/a",
}

metric_info["mem_nonheap_committed"] = {
    "title" : _("Non-heap memory committed"),
    "unit"  : "bytes",
    "color" : "16/b",
}

metric_info["processes"] = {
    "title" : _("Processes"),
    "unit"  : "count",
    "color" : "#8040f0",
}

metric_info["threads"] = {
    "title" : _("Threads"),
    "unit"  : "count",
    "color" : "#8040f0",
}

metric_info["threads_idle"] = {
    "title" : _("Idle threads"),
    "unit"  : "count",
    "color" : "#8040f0",
}

metric_info["threads_rate"] = {
    "title" : _("Threads per second"),
    "unit"  : "1/s",
    "color" : "44/a",
}

metric_info["threads_daemon"] = {
    "title" : _("Daemon threads"),
    "unit"  : "count",
    "color" : "32/a",
}

metric_info["threads_max"] = {
    "title" : _("Maximum number of threads"),
    "help"  : _("Maximum number of threads started at any given time during the JVM lifetime"),
    "unit"  : "count",
    "color" : "35/a",
}

metric_info["threads_total"] = {
    "title" : _("Number of threads since starting JVM"),
    "unit"  : "count",
    "color" : "41/a",
}

metric_info["threads_busy"] = {
    "title" : _("Busy threads"),
    "unit"  : "count",
    "color" : "34/a",
}

metric_info["vol_context_switches"] = {
    "title" : _("Voluntary context switches"),
    "help"  : _("A voluntary context switch occurs when a thread blocks because it requires a resource that is unavailable"),
    "unit"  : "count",
    "color" : "36/a",
}

metric_info["invol_context_switches"] = {
    "title" : _("Involuntary context switches"),
    "help"  : _("An involuntary context switch takes place when a thread executes for the duration of its time slice or when the system identifies a higher-priority thread to run"),
    "unit"  : "count",
    "color" : "45/b",
}

metric_info["tapes_total"] = {
    "title" : _("Total number of tapes"),
    "unit"  : "count",
    "color" : "#8040f0",
}

metric_info["tapes_free"] = {
    "title" : _("Free tapes"),
    "unit"  : "count",
    "color" : "#8044ff",
}

metric_info["tapes_util"] = {
    "title" : _("Tape utilization"),
    "unit"  : "%",
    "color" : "#ff8020",
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
    "color" : "16/a"
}

metric_info["cifs_share_users"] = {
    "title" : _("Users using a cifs share"),
    "unit"  : "count",
    "color" : "#60f020",
}

metric_info["smoke_ppm"] = {
    "title" : _("Smoke"),
    "unit"  : "%/m",
    "color" : "#60f088",
}

metric_info["deviation_calibration_point"] = {
    "title" : _("Deviation from calibration point"),
    "unit"  : "%",
    "color" : "#60f020",
}

metric_info["deviation_airflow"] = {
    "title" : _("Airflow deviation"),
    "unit"  : "%",
    "color" : "#60f020",
}

# TODO: user -> cpu_util_user
metric_info["user"] = {
    "title" : _("User"),
    "help"  : _("CPU time spent in user space"),
    "unit"  : "%",
    "color" : "#60f020",
}

# metric_info["cpu_util_privileged"] = {
#     "title" : _("Privileged"),
#     "help"  : _("CPU time spent in privileged mode"),
#     "unit"  : "%",
#     "color" : "23/a",
# }

metric_info["nice"] = {
    "title" : _("Nice"),
    "help"  : _("CPU time spent in user space for niced processes"),
    "unit"  : "%",
    "color" : "#ff9050",
}

metric_info["interrupt"] = {
    "title" : _("Interrupt"),
    "unit"  : "%",
    "color" : "#ff9050",
}

metric_info["system"] = {
    "title" : _("System"),
    "help"  : _("CPU time spent in kernel space"),
    "unit"  : "%",
    "color" : "#ff6000",
}

metric_info["io_wait"] = {
    "title" : _("I/O-wait"),
    "help"  : _("CPU time spent waiting for I/O"),
    "unit"  : "%",
    "color" : "#00b0c0",
}

metric_info["cpu_util_guest"] = {
    "title" : _("Guest operating systems"),
    "help"  : _("CPU time spent for executing guest operating systems"),
    "unit"  : "%",
    "color" : "12/a",
}

metric_info["cpu_util_steal"] = {
    "title" : _("Steal"),
    "help"  : _("CPU time stolen by other operating systems"),
    "unit"  : "%",
    "color" : "16/a",
}

metric_info["idle"] = {
    "title" : _("Idle"),
    "help"  : _("CPU idle time"),
    "unit"  : "%",
    "color" : "#805022",
}

metric_info["fpga_util"] = {
    "title" : _("FPGA utilization"),
    "unit"  : "%",
    "color" : "#60f020",
}

metric_info["util"] = {
    "title" : _("CPU utilization"),
    "unit"  : "%",
    "color" : "26/a",
}

metric_info["util_average"] = {
    "title" : _("CPU utilization (average)"),
    "unit"  : "%",
    "color" : "26/b",
}

metric_info["util1s"] = {
    "title" : _("CPU utilization last second"),
    "unit"  : "%",
    "color" : "#50ff20",
}

metric_info["util5s"] = {
    "title" : _("CPU utilization last five seconds"),
    "unit"  : "%",
    "color" : "#600020",
}

metric_info["util1"] = {
    "title" : _("CPU utilization last minute"),
    "unit"  : "%",
    "color" : "#60f020",
}

metric_info["util5"] = {
    "title" : _("CPU utilization last 5 minutes"),
    "unit"  : "%",
    "color" : "#80f040",
}

metric_info["util15"] = {
    "title" : _("CPU utilization last 15 minutes"),
    "unit"  : "%",
    "color" : "#9a52bf",
}

metric_info["time_offset"] = {
    "title" : _("Time offset"),
    "unit"  : "s",
    "color" : "#9a52bf",
}

metric_info["jitter"] = {
    "title" : _("Time dispersion"),
    "unit"  : "s",
    "color" : "43/b",
}

metric_info["connection_time"] = {
    "title" : _("Connection time"),
    "unit"  : "s",
    "color" : "#94b65a",
}

metric_info["connections"] = {
    "title" : _("Connections"),
    "unit"  : "count",
    "color" : "#a080b0",
}

metric_info["connections_async_writing"] = {
    "title" : _("Asynchronous writing connections"),
    "unit"  : "count",
    "color" : "16/a",
}

metric_info["connections_async_keepalive"] = {
    "title" : _("Asynchronous keep alive connections"),
    "unit"  : "count",
    "color" : "22/a",
}

metric_info["connections_async_closing"] = {
    "title" : _("Asynchronous closing connections"),
    "unit"  : "count",
    "color" : "24/a",
}

metric_info["connections_rate"] = {
    "title" : _("Connections per second"),
    "unit"  : "1/s",
    "color" : "#a080b0",
}

metric_info["requests_per_second"] = {
    "title" : _("Requests per second"),
    "unit"  : "1/s",
    "color" : "#4080a0",
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

metric_info["busy_workers"] = {
    "title" : _("Busy workers"),
    "unit"  : "count",
    "color" : "#a080b0",
}

metric_info["idle_workers"] = {
    "title" : _("Idle workers"),
    "unit"  : "count",
    "color" : "43/b",
}

metric_info["open_slots"] = {
    "title" : _("Open slots"),
    "unit"  : "count",
    "color" : "31/a",
}

metric_info["total_slots"] = {
    "title" : _("Total slots"),
    "unit"  : "count",
    "color" : "33/b",
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
    "color" : "42/a",
}

metric_info["rejected_sessions"] = {
    "title" : _("Rejected sessions"),
    "unit"  : "count",
    "color" : "45/a",
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

metric_info["disk_ios"] = {
    "title" : _("Disk I/O operations"),
    "unit"  : "1/s",
    "color" : "#60e0a0",
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
    "title" : _("Write wait time"), "unit" : "s", "color" : "#20c0e8",
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

metric_info["read_latency"] = {
    "title" : _("Read latency"),
    "unit"  : "s",
    "color" : "35/a",
}

metric_info["write_latency"] = {
    "title" : _("Write latency"),
    "unit"  : "s",
    "color" : "45/a",
}

metric_info["disk_queue_length"] = {
    "title" : _("Average disk I/O-queue length"),
    "unit"  : "",
    "color" : "#7060b0",
}

metric_info["disk_utilization"] = {
    "title" : _("Disk utilization"),
    "unit"  : "ratio",
    "color" : "#a05830",
}

metric_info["disk_capacity"] = {
    "title" : _("Total disk capacity"),
    "unit"  : "bytes",
    "color" : "12/a",
}

metric_info["disks"] = {
    "title" : _("Disks"),
    "unit"  : "count",
    "color" : "41/a",
}

metric_info["spare_disks"] = {
    "title" : _("Spare disk"),
    "unit"  : "count",
    "color" : "26/a",
}

metric_info["failed_disks"] = {
    "title" : _("Failed disk"),
    "unit"  : "count",
    "color" : "13/a",
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
    "title" : _("Execution time"),
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

metric_info["sync_latency"] = {
    "title" : _("Sync latency"),
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

metric_info["read_blocks"] = {
    "title" : _("Read blocks per second"),
    "unit"  : "1/s",
    "color" : "11/a",
}

metric_info["write_blocks"] = {
    "title" : _("Write blocks per second"),
    "unit"  : "1/s",
    "color" : "21/a",
}

metric_info["broadcast_packets"] = {
    "title" : _("Broadcast packets"),
    "unit"  : "1/s",
    "color" : "11/a",
}

metric_info["multicast_packets"] = {
    "title" : _("Multicast packets"),
    "unit"  : "1/s",
    "color" : "14/a",
}

metric_info["fc_rx_bytes"] = {
    "title" : _("Input"),
    "unit"  : "bytes/s",
    "color" : "31/a",
}

metric_info["fc_tx_bytes"] = {
    "title" : _("Output"),
    "unit"  : "bytes/s",
    "color" : "35/a",
}

metric_info["fc_rx_frames"] = {
    "title" : _("Received Frames"),
    "unit"  : "1/s",
    "color" : "31/b",
}

metric_info["fc_tx_frames"] = {
    "title" : _("Transmitted Frames"),
    "unit"  : "1/s",
    "color" : "35/b",
}

metric_info["fc_crc_errors"] = {
    "title" : _("Receive CRC errors"),
    "unit"  : "1/s",
    "color" : "12/a",
}

metric_info["fc_encouts"] = {
    "title" : _("Enc-Outs"),
    "unit"  : "1/s",
    "color" : "13/a",
}

metric_info["fc_c3discards"] = {
    "title" : _("C3 discards"),
    "unit"  : "1/s",
    "color" : "14/a",
}

metric_info["fc_notxcredits"] = {
    "title" : _("No TX Credits"),
    "unit"  : "1/s",
    "color" : "15/a",
}

metric_info["fc_c2c3_discards"] = {
    "title" : _("C2 and c3 discards"),
    "unit"  : "1/s",
    "color" : "15/a",
}

metric_info["fc_link_fails"] = {
    "title" : _("Link failures"),
    "unit"  : "1/s",
    "color" : "11/a",
}

metric_info["fc_sync_losses"] = {
    "title" : _("Sync losses"),
    "unit"  : "1/s",
    "color" : "12/a",
}

metric_info["fc_prim_seq_errors"] = {
    "title" : _("Primitive sequence errors"),
    "unit"  : "1/s",
    "color" : "13/a",
}

metric_info["fc_invalid_tx_words"] = {
    "title" : _("Invalid TX words"),
    "unit"  : "1/s",
    "color" : "14/a",
}

metric_info["fc_invalid_crcs"] = {
    "title" : _("Invalid crcs"),
    "unit"  : "1/s",
    "color" : "15/a",
}

metric_info["fc_address_id_errors"] = {
    "title" : _("Address ID errors"),
    "unit"  : "1/s",
    "color" : "16/a",
}

metric_info["fc_link_resets_in"] = {
    "title" : _("Link resets in"),
    "unit"  : "1/s",
    "color" : "21/a",
}

metric_info["fc_link_resets_out"] = {
    "title" : _("Link resets out"),
    "unit"  : "1/s",
    "color" : "22/a",
}

metric_info["fc_offline_seqs_in"] = {
    "title" : _("Offline sequences in"),
    "unit"  : "1/s",
    "color" : "23/a",
}

metric_info["fc_offline_seqs_out"] = {
    "title" : _("Offline sequences out"),
    "unit"  : "1/s",
    "color" : "24/a",
}

metric_info["fc_c2_fbsy_frames"] = {
    "title" : _("F_BSY frames"),
    "unit"  : "1/s",
    "color" : "25/a",
}

metric_info["fc_c2_frjt_frames"] = {
    "title" : _("F_RJT frames"),
    "unit"  : "1/s",
    "color" : "26/a",
}


metric_info["rmon_packets_63"] = {
    "title" : _("Packets of size 0-63 bytes"),
    "unit"  : "1/s",
    "color" : "21/a",
}

metric_info["rmon_packets_127"] = {
    "title" : _("Packets of size 64-127 bytes"),
    "unit"  : "1/s",
    "color" : "24/a",
}

metric_info["rmon_packets_255"] = {
    "title" : _("Packets of size 128-255 bytes"),
    "unit"  : "1/s",
    "color" : "31/a",
}

metric_info["rmon_packets_511"] = {
    "title" : _("Packets of size 256-511 bytes"),
    "unit"  : "1/s",
    "color" : "34/a",
}

metric_info["rmon_packets_1023"] = {
    "title" : _("Packets of size 512-1023 bytes"),
    "unit"  : "1/s",
    "color" : "41/a",
}

metric_info["rmon_packets_1518"] = {
    "title" : _("Packets of size 1024-1518 bytes"),
    "unit"  : "1/s",
    "color" : "44/a",
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

metric_info["fw_connections_active"] = {
    "title" : _("Active connections"),
    "unit"  : "count",
    "color" : "15/a",
}

metric_info["fw_connections_established"] = {
    "title" : _("Established connections"),
    "unit"  : "count",
    "color" : "41/a",
}

metric_info["fw_connections_halfopened"] = {
    "title" : _("Half opened connections"),
    "unit"  : "count",
    "color" : "16/a",
}

metric_info["fw_connections_halfclosed"] = {
    "title" : _("Half closed connections"),
    "unit"  : "count",
    "color" : "11/a",
}

metric_info["fw_connections_passthrough"] = {
    "title" : _("Unoptimized connections"),
    "unit"  : "count",
    "color" : "34/a",
}

metric_info["host_check_rate"] = {
    "title" : _("Host check rate"),
    "unit"  : "1/s",
    "color" : "#884422",
}

metric_info["hosts_active"] = {
    "title" : _("Active hosts"),
    "unit"  : "count",
    "color" : "11/a",
}

metric_info["hosts_inactive"] = {
    "title" : _("Inactive hosts"),
    "unit"  : "count",
    "color" : "16/a",
}

metric_info["hosts_degraded"] = {
    "title" : _("Degraded hosts"),
    "unit"  : "count",
    "color" : "23/a",
}

metric_info["hosts_offline"] = {
    "title" : _("Offline hosts"),
    "unit"  : "count",
    "color" : "31/a",
}

metric_info["hosts_other"] = {
    "title" : _("Other hosts"),
    "unit"  : "count",
    "color" : "41/a",
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

metric_info["free_dhcp_leases"] = {
    "title" : _("Free DHCP leases"),
    "unit"  : "count",
    "color" : "34/a",
}

metric_info["pending_dhcp_leases"] = {
    "title" : _("Pending DHCP leases"),
    "unit"  : "count",
    "color" : "31/a",
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

metric_info["mail_queue_deferred_length"] = {
    "title" : _("Length of deferred mail queue"),
    "unit"  : "count",
    "color" : "#40a0b0",
}

metric_info["mails_received_time"] = {
    "title" : _("Received mails"),
    "unit"  : "s",
    "color" : "31/a",
}

metric_info["mail_queue_deferred_size"] = {
    "title" : _("Size of deferred mail queue"),
    "unit"  : "bytes",
    "color" : "#402010",
}

metric_info["mail_queue_active_length"] = {
    "title" : _("Length of active mail queue"),
    "unit"  : "count",
    "color" : "#ff6000",
}

metric_info["pages_total"] = {
    "title" : _("Total printed pages"),
    "unit"  : "count",
    "color" : "#939393",
}

metric_info["pages_color"] = {
    "title" : _("Color"),
    "unit"  : "count",
    "color" : "#0010f4",
}

metric_info["pages_bw"] = {
    "title" : _("B/W"),
    "unit"  : "count",
    "color" : "#111111",
}

metric_info["pages_a4"] = {
    "title" : _("A4"),
    "unit"  : "count",
    "color" : "#45f1ff",
}

metric_info["pages_a3"] = {
    "title" : _("A3"),
    "unit"  : "count",
    "color" : "#48c9fb",
}

metric_info["pages_color_a4"] = {
    "title" : _("Color A4"),
    "unit"  : "count",
    "color" : "#007ff4",
}

metric_info["pages_bw_a4"] = {
    "title" : _("B/W A4"),
    "unit"  : "count",
    "color" : "#2f2f2f",
}

metric_info["pages_color_a3"] = {
    "title" : _("Color A3"),
    "unit"  : "count",
    "color" : "#138eff",
}

metric_info["pages_bw_a3"] = {
    "title" : _("B/W A3"),
    "unit"  : "count",
    "color" : "#3c3c3c",
}

metric_info["supply_toner_cyan"] = {
    "title" : _("Supply toner cyan"),
    "unit"  : "%",
    "color" : "#00ffff",
}

metric_info["supply_toner_magenta"] = {
    "title" : _("Supply toner magenta"),
    "unit"  : "%",
    "color" : "#ff00ff",
}

metric_info["supply_toner_yellow"] = {
    "title" : _("Supply toner yellow"),
    "unit"  : "%",
    "color" : "#ffff00",
}

metric_info["supply_toner_black"] = {
    "title" : _("Supply toner black"),
    "unit"  : "%",
    "color" : "#000000",
}

metric_info["pressure"] = {
    "title" : _("Pressure"),
    "unit"  : "bar",
    "color" : "#ff6234",
}

metric_info["licenses"] = {
    "title" : _("Used licenses"),
    "unit"  : "count",
    "color" : "#ff6234",
}

metric_info["files_open"] = {
    "title" : _("Open files"),
    "unit"  : "count",
    "color" : "#ff6234",
}

metric_info["directories"] = {
    "title" : _("Directories"),
    "unit"  : "count",
    "color" : "#202020",
}

metric_info["shared_memory_segments"] = {
    "title" : _("Shared memory segments"),
    "unit"  : "count",
    "color" : "#606060",
}

metric_info["semaphore_ids"] = {
    "title" : _("IPC semaphore IDs"),
    "unit"  : "count",
    "color" : "#404040",
}

metric_info["semaphores"] = {
    "title" : _("IPC semaphores"),
    "unit"  : "count",
    "color" : "#ff4534",
}

metric_info["backup_size"] = {
    "title" : _("Backup size"),
    "unit"  : "bytes",
    "color" : "12/a",
}

metric_info["backup_avgspeed"] = {
    "title" : _("Average speed of backup"),
    "unit"  : "bytes/s",
    "color" : "22/a",
}

metric_info["backup_duration"] = {
    "title" : _("Duration of backup"),
    "unit"  : "s",
    "color" : "33/a",
}

metric_info["job_duration"] = {
    "title" : _("Job duration"),
    "unit"  : "s",
    "color" : "33/a",
}

metric_info["checkpoint_age"] = {
    "title" : _("Time since last checkpoint"),
    "unit"  : "s",
    "color" : "#006040",
}

metric_info["backup_age"] = {
    "title" : _("Time since last backup"),
    "unit"  : "s",
    "color" : "34/a",
}

metric_info["logswitches_last_hour"] = {
    "title" : _("Log switches in the last 60 minutes"),
    "unit"  : "count",
    "color" : "#006040",
}

metric_info["database_apply_lag"] = {
    "title" : _("Database apply lag"),
    "help"  : _("Amount of time that the application of redo data on the standby database lags behind the primary database"),
    "unit"  : "s",
    "color" : "#006040",
}

metric_info["direct_io"] = {
    "title" : _("Direct I/O"),
    "unit"  : "bytes/s",
    "color" : "#006040",
}

metric_info["buffered_io"] = {
    "title" : _("Buffered I/O"),
    "unit"  : "bytes/s",
    "color" : "#006040",
}

metric_info["write_cache_usage"] = {
    "title" : _("Write cache usage"),
    "help"  : _("A write cache is a cache that uses an allocate on write miss, write-back, no allocate on read miss strategy"),
    "unit"  : "%",
    "color" : "#030303",
}

metric_info["total_cache_usage"] = {
    "title" : _("Total cache usage"),
    "unit"  : "%",
    "color" : "#0ae86d",
}

# TODO: "title" darf nicht mehr info enthalten als die ID
# TODO: Was heißt Garbage collection? Dauer? Anzahl pro Zeit?
# Größe in MB???
metric_info["gc_reclaimed_redundant_memory_areas"] = {
    "title" : _("Reclaimed redundant memory areas"),
    "help"  : _("The garbage collector attempts to reclaim garbage, or memory occupied by objects that are no longer in use by a program"),
    "unit"  : "count",
    "color" : "31/a",
}

# TODO: ? GCs/sec? oder Avg time? Oder was?
metric_info["gc_reclaimed_redundant_memory_areas_time"] = {
    "title" : _("Reclaiming redundant memory areas"),
    "unit"  : "1/s",
    "color" : "32/a",
}

metric_info["net_data_recv"] = {
    "title" : _("Net data received"),
    "unit"  : "bytes/s",
    "color" : "41/b",
}

metric_info["net_data_sent"] = {
    "title" : _("Net data sent"),
    "unit"  : "bytes/s",
    "color" : "42/a",
}

for ty, unit in [ ("requests", "1/s"), ("bytes", "bytes/s"), ("secs", "1/s") ]:
    metric_info[ty+"_cmk_views"] = {
        "title" : _("Check_MK: Views"),
        "unit"  : unit,
        "color" : "#ff8080",
    }

    metric_info[ty + "_cmk_wato"] = {
        "title" : _("Check_MK: WATO"),
        "unit"  : unit,
        "color" : "#377cab",
    }

    metric_info[ty + "_cmk_bi"] = {
        "title" : _("Check_MK: BI"),
        "unit"  : unit,
        "color" : "#4eb0f2",
    }

    metric_info[ty + "_cmk_snapins"] = {
        "title" : _("Check_MK: Snapins"),
        "unit"  : unit,
        "color" : "#ff4040",
    }

    metric_info[ty + "_cmk_dashboards"] = {
        "title" : _("Check_MK: Dashboards"),
        "unit"  : unit,
        "color" : "#4040ff",
    }

    metric_info[ty + "_cmk_other"] = {
        "title" : _("Check_MK: Other"),
        "unit"  : unit,
        "color" : "#5bb9eb",
    }

    metric_info[ty + "_nagvis_snapin"] = {
        "title" : _("NagVis: Snapin"),
        "unit"  : unit,
        "color" : "#f2904e",
    }

    metric_info[ty + "_nagvis_ajax"] = {
        "title" : _("NagVis: AJAX"),
        "unit"  : unit,
        "color" : "#af91eb",
    }

    metric_info[ty + "_nagvis_other"] = {
        "title" : _("NagVis: Other"),
        "unit"  : unit,
        "color" : "#f2df40",
    }

    metric_info[ty + "_images"] = {
        "title" : _("Image"),
        "unit"  : unit,
        "color" : "#91cceb",
    }

    metric_info[ty + "_styles"] = {
        "title" : _("Styles"),
        "unit"  : unit,
        "color" : "#c6f24e",
    }

    metric_info[ty + "_scripts"] = {
        "title" : _("Scripts"),
        "unit"  : unit,
        "color" : "#4ef26c",
    }

    metric_info[ty + "_other"] = {
        "title" : _("Other"),
        "unit"  : unit,
        "color" : "#4eeaf2",
    }


metric_info["total_modems"] = {
    "title" : _("Total number of modems"),
    "unit"  : "count",
    "color" : "12/c",
}

metric_info["active_modems"] = {
    "title" : _("Active modems"),
    "unit"  : "count",
    "color" : "14/c",
}

metric_info["registered_modems"] = {
    "title" : _("Registered modems"),
    "unit"  : "count",
    "color" : "16/c",
}

metric_info["channel_utilization"] = {
    "title" : _("Channel utilization"),
    "unit"  : "%",
    "color" : "24/c",
}

metric_info["frequency"] = {
    "title" : _("Frequency"),
    "unit"  : "hz",
    "color" : "11/c",
}

metric_info["battery_capacity"] = {
    "title" : _("Battery capacity"),
    "unit"  : "%",
    "color" : "11/c",
}

metric_info["battery_current"] = {
    "title" : _("Battery electrical current"),
    "unit"  : "a",
    "color" : "15/a",
}

metric_info["battery_temp"] = {
    "title" : _("Battery temperature"),
    "unit"  : "c",
    "color" : "#ffb030",
}

metric_info["connector_outlets"] = {
    "title" : _("Connector outlets"),
    "unit"  : "count",
    "color" : "51/a",
}

metric_info["qos_dropped_bytes_rate"] = {
    "title" : _("Qos dropped bytes"),
    "unit"  : "bytes/s",
    "color" : "41/a",
}

metric_info["qos_outbound_bytes_rate"] = {
    "title" : _("Qos outbound bytes"),
    "unit"  : "bytes/s",
    "color" : "26/a",
}

metric_info["apache_state_startingup"] = {
    "title" : _("Apache starting up"),
    "unit"  : "count",
    "color" : "11/a",
}

metric_info["apache_state_waiting"] = {
    "title" : _("Apache writing"),
    "unit"  : "count",
    "color" : "14/a",
}

metric_info["apache_state_logging"] = {
    "title" : _("Apache logging"),
    "unit"  : "count",
    "color" : "21/a",
}

metric_info["apache_state_dns"] = {
    "title" : _("Apache DNS"),
    "unit"  : "count",
    "color" : "24/a",
}

metric_info["apache_state_sending_reply"] = {
    "title" : _("Apache sending reply"),
    "unit"  : "count",
    "color" : "31/a",
}

metric_info["apache_state_reading_request"] = {
    "title" : _("Apache reading request"),
    "unit"  : "count",
    "color" : "34/a",
}

metric_info["apache_state_closing"] = {
    "title" : _("Apache closing"),
    "unit"  : "count",
    "color" : "41/a",
}

metric_info["apache_state_idle_cleanup"] = {
    "title" : _("Apache idle clean up"),
    "unit"  : "count",
    "color" : "44/a",
}

metric_info["apache_state_finishing"] = {
    "title" : _("Apache finishing"),
    "unit"  : "count",
    "color" : "46/b",
}

metric_info["apache_state_keep_alive"] = {
    "title" : _("Apache keep alive"),
    "unit"  : "count",
    "color" : "53/b",
}

metric_info["http_bandwidth"] = {
    "title" : _("Http bandwidth"),
    "unit"  : "bytes/s",
    "color" : "53/b",
}

# netapp api volumes

for volume_info in [ "NFS", "CIFS", "SAN", "FCP", "ISCSI" ]:
    for what, unit in [ ("data", "bytes"), ("latency", "s") ]:

        volume = volume_info.lower()

        metric_info[ "%s_read_%s" % (volume, what) ] = {
            "title" : _( "%s read %s" % (volume_info, what) ),
            "unit"  : unit,
            "color" : "31/a",
        }

        metric_info[ "%s_write_%s" % (volume, what) ] = {
            "title" : _( "%s write %s" % (volume_info, what) ),
            "unit"  : unit,
            "color" : "44/a",
        }

metric_info["harddrive_power_cycles"] = {
    "title" : _("Harddrive power cycles"),
    "unit"  : "count",
    "color" : "11/a",
}

metric_info["harddrive_reallocated_sectors"] = {
    "title" : _("Harddrive reallocated sectors"),
    "unit"  : "count",
    "color" : "14/a",
}

metric_info["harddrive_reallocated_events"] = {
    "title" : _("Harddrive reallocated events"),
    "unit"  : "count",
    "color" : "21/a",
}

metric_info["harddrive_spin_retries"] = {
    "title" : _("Harddrive spin retries"),
    "unit"  : "count",
    "color" : "24/a",
}

metric_info["harddrive_pending_sectors"] = {
    "title" : _("Harddrive pending sectors"),
    "unit"  : "count",
    "color" : "31/a",
}

metric_info["harddrive_cmd_timeouts"] = {
    "title" : _("Harddrive command timeouts"),
    "unit"  : "count",
    "color" : "34/a",
}

metric_info["harddrive_end_to_end_errors"] = {
    "title" : _("Harddrive end-to-end errors"),
    "unit"  : "count",
    "color" : "41/a",
}

metric_info["harddrive_uncorrectable_erros"] = {
    "title" : _("Harddrive uncorrectable errors"),
    "unit"  : "count",
    "color" : "44/a",
}

metric_info["harddrive_udma_crc_errors"] = {
    "title" : _("Harddrive udma crc errors"),
    "unit"  : "count",
    "color" : "46/a",
}

metric_info["ap_devices_total"] = {
    "title" : _("Total devices"),
    "unit"  : "count",
    "color" : "51/a"
}

metric_info["ap_devices_drifted"] = {
    "title" : _("Time drifted devices"),
    "unit"  : "count",
    "color" : "23/a"
}

metric_info["ap_devices_not_responding"] = {
    "title" : _("Not responding devices"),
    "unit"  : "count",
    "color" : "14/a"
}

metric_info["request_rate"] = {
    "title" : _("Request rate"),
    "unit"  : "1/s",
    "color" : "34/a",
}

metric_info["error_rate"] = {
    "title" : _("Error rate"),
    "unit"  : "1/s",
    "color" : "14/a",
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

check_metrics["check_mk_active-mail_loop"] = {
    "duration" : { "name": "mails_received_time" }
}

check_metrics["check_mk_active-http"] = {
    "time" : { "name": "responese_time" },
    "size" : { "name": "http_bandwidth" },
}

check_metrics["check_mk_active-tcp"] = {
    "time" : { "name": "response_time" }
}

check_metrics["check-mk-host-tcp"] = {
    "time" : { "name": "response_time" }
}

check_metrics["check_mk-netapp_api_volumes"] = {
    "nfs_read_latency"      : { "scale" : m },
    "nfs_write_latency"     : { "scale" : m },
    "cifs_read_latency"     : { "scale" : m },
    "cifs_write_latency"    : { "scale" : m },
    "san_read_latency"      : { "scale" : m },
    "san_write_latency"     : { "scale" : m },
    "fcp_read_latency"      : { "scale" : m },
    "fcp_write_latency"     : { "scale" : m },
    "iscsi_read_latency"    : { "scale" : m },
    "iscsi_write_latency"   : { "scale" : m },
}

check_metrics["check_mk_active-tcp"] = {
    "time" : { "name": "response_time" }
}

check_metrics["check-mk-host-tcp"] = {
    "time" : { "name": "response_time" }
}

check_metrics["check_mk-jolokia_metrics.gc"] = {
    "CollectionCount" : { "name" : "gc_reclaimed_redundant_memory_areas" },
    "CollectionTime"  : { "name" : "gc_reclaimed_redundant_memory_areas_time", "scale" : 1/60 },
}

check_metrics["check_mk-rmon_stats"] = {
    "0-63b"     : { "name" : "rmon_packets_63" },
    "64-127b"   : { "name" : "rmon_packets_127" },
    "128-255b"  : { "name" : "rmon_packets_255" },
    "256-511b"  : { "name" : "rmon_packets_511" },
    "512-1023b" : { "name" : "rmon_packets_1023" },
    "1024-1518b": { "name" : "rmon_packets_1518" },
}

check_metrics["check_mk-cpu.loads"] = {
   " load5" : { "auto_graph" : False }
}

check_metrics["check_mk-ucd_cpu_load"] = {
    "load5" : { "auto_graph" : False }
}

check_metrics["check_mk-hpux_cpu"] = {
    "wait" : { "name" : "io_wait" }
}

check_metrics["check_mk-hitachi_hnas_cpu"] = {
    "cpu_util" : { "name" : "util" }
}

check_metrics["check_mk-statgrab_disk"] = {
    "read"  : { "name" : "disk_read_throughput" },
    "write" : { "name" : "disk_write_throughput" }
}

check_metrics["check_mk-ibm_svc_systemstats.diskio"] = {
    "read"  : { "name" : "disk_read_throughput" },
    "write" : { "name" : "disk_write_throughput" }
}

check_metrics["check_mk-ibm_svc_nodestats.diskio"] = {
    "read"  : { "name" : "disk_read_throughput" },
    "write" : { "name" : "disk_write_throughput" }
}

check_metrics["check_mk-netscaler_mem"] = {
    "mem"  : { "name" : "mem_used" }
}

ram_used_swap_translation = {
    "ramused"  : { "name" : "mem_used",  "scale" : MB },
    "swapused" : { "name" : "swap_used", "scale" : MB },
    "memused"  : { "name" : "mem_total", "scale" : MB },
}

check_metrics["check_mk-statgrab_mem"] = ram_used_swap_translation
check_metrics["check_mk-hr_mem"] = ram_used_swap_translation

check_metrics["check_mk-mem.used"] = {
    "ramused"       : { "name" : "mem_used",  "scale" : MB },
    "swapused"      : { "name" : "swap_used", "scale" : MB },
    "memused"       : { "name" : "mem_total", "scale" : MB },
    "shared"        : { "name" : "mem_lnx_shmem", "scale" : MB },
    "pagetable"     : { "name" : "mem_lnx_page_tables", "scale" : MB },
    "mapped"        : { "name" : "mem_lnx_mapped", "scale" : MB },
    "committed_as"  : { "name" : "mem_lnx_committed_as", "scale" : MB },
}

check_metrics["check_mk-ibm_svc_nodestats.disk_latency"] = {
    "read_latency"  : { "scale" : m },
    "write_latency" : { "scale" : m },
}

check_metrics["check_mk-ibm_svc_systemstats.disk_latency"] = {
    "read_latency"  : { "scale" : m },
    "write_latency" : { "scale" : m },
}

check_metrics["check_mk-netapp_api_disk.summary"] = {
    "total_disk_capacity"   : { "name" : "disk_capacity" },
    "total_disks"           : { "name" : "disks" },
}

check_metrics["check_mk-emc_isilon_iops"] = {
    "iops" : { "name" : "disk_ios" }
}

check_metrics["check_mk-vms_system.ios"] = {
    "direct"   : { "name" : "direct_io" },
    "buffered" : { "name" : "buffered_io" }
}

check_metrics["check_mk-kernel"] = {
    "ctxt"       : { "name": "context_switches" },
    "pgmajfault" : { "name": "major_page_faults" },
    "processes"  : { "name": "process_creations" },
}

check_metrics["check_mk-oracle_jobs"] = {
    "duration" : { "name" : "job_duration" }
}

check_metrics["check_mk-vms_system.procs"] = {
    "procs" : { "name" : "processes" }
}

check_metrics["check_mk-jolokia_metrics.tp"] = {
    "currentThreadCount" : { "name" : "threads_idle" },
    "currentThreadsBusy" : { "name" : "threads_busy" },
}

check_metrics["check_mk-aix_memory"] = {
    "ramused" : { "name" : "mem_used", "scale": MB },
    "swapused" : { "name" : "swap_used", "scale": MB }
}

check_metrics["check_mk-mem.win"] = {
    "memory" : { "name" : "mem_used", "scale" : MB },
    "pagefile" : { "name" : "pagefile_used", "scale" : MB }
}

check_metrics["check_mk-brocade_mlx.module_mem"] = {
    "memused" : { "name" : "mem_used" }
}

check_metrics["check_mk-jolokia_metrics.mem"] = {
    "heap"    : { "name" : "mem_heap" , "scale" : MB },
    "nonheap" : { "name" : "mem_nonheap", "scale" : MB }
}

check_metrics["check_mk-jolokia_metrics.threads"] = {
    "ThreadRate"        : { "name" : "threads_rate" },
    "ThreadCount"       : { "name" : "threads" },
    "DeamonThreadCount" : { "name" : "threads_daemon" },
    "PeakThreadCount"   : { "name" : "threads_max" },
    "TotalStartedThreadCount" : { "name" : "threads_total" },
}

check_metrics["check_mk-mem.linux"] = {
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

check_metrics["check_mk-mem.vmalloc"] = {
    "used"  : { "name" : "mem_lnx_vmalloc_used" },
    "chunk" : { "name" : "mem_lnx_vmalloc_chunk" }
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

check_metrics["check_mk_active-disk_smb"] = {
    "~.*" : { "name" : "fs_used" }
}

df_translation = {
    "~(?!inodes_used|fs_size|growth|trend|fs_provisioning).*"   : { "name"  : "fs_used", "scale" : MB },
    "fs_size" : { "scale" : MB },
    "growth"  : { "name"  : "fs_growth", "scale" : MB / 86400.0 },
    "trend"   : { "name"  : "fs_trend", "scale" : MB / 86400.0 },
}

check_metrics["check_mk-df"]                                    = df_translation
check_metrics["check_mk-esx_vsphere_datastores"]                = df_translation
check_metrics["check_mk-netapp_api_aggr"]                       = df_translation
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
check_metrics["check_mk-netapp_api_volume"]                     = df_translation

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

check_metrics["check_mk-esx_vsphere_counters"]      = if_translation
check_metrics["check_mk-esx_vsphere_counters.if"]   = if_translation
check_metrics["check_mk-fritz"]                     = if_translation
check_metrics["check_mk-fritz.wan_if"]              = if_translation
check_metrics["check_mk-hitachi_hnas_fc_if"]        = if_translation
check_metrics["check_mk-if64"]                      = if_translation
check_metrics["check_mk-hpux_if"]                   = if_translation
check_metrics["check_mk-if64_tplink"]               = if_translation
check_metrics["check_mk-if_lancom"]                 = if_translation
check_metrics["check_mk-if"]                        = if_translation
check_metrics["check_mk-lnx_if"]                    = if_translation
check_metrics["check_mk-mcdata_fcport"]             = if_translation
check_metrics["check_mk-netapp_api_if"]             = if_translation
check_metrics["check_mk-statgrab_net"]              = if_translation
check_metrics["check_mk-ucs_bladecenter_if"]        = if_translation
check_metrics["check_mk-vms_if"]                    = if_translation
check_metrics["check_mk-winperf_if"]                = if_translation
check_metrics["check_mk-emc_vplex_if"]              = if_translation

check_metrics["check_mk-brocade_fcport"] = {
    "in"             : { "name": "fc_rx_bytes", },
    "out"            : { "name": "fc_tx_bytes", },
    "rxframes"       : { "name": "fc_rx_frames", },
    "txframes"       : { "name": "fc_tx_frames", },
    "rxcrcs"         : { "name": "fc_crc_errors" },
    "rxencoutframes" : { "name": "fc_encouts" },
    "c3discards"     : { "name": "fc_c3discards" },
    "notxcredits"    : { "name": "fc_notxcredits" },
}

check_metrics["check_mk-fc_port"] = {
    "in"             : { "name": "fc_rx_bytes", },
    "out"            : { "name": "fc_tx_bytes", },
    "rxobjects"      : { "name": "fc_rx_frames", },
    "txobjects"      : { "name": "fc_tx_frames", },
    "rxcrcs"         : { "name": "fc_crc_errors" },
    "rxencoutframes" : { "name": "fc_encouts" },
    "c3discards"     : { "name": "fc_c3discards" },
    "notxcredits"    : { "name": "fc_notxcredits" },
}

check_metrics["check_mk-qlogic_fcport"] = {
    "in"                    : { "name" : "fc_rx_bytes", },
    "out"                   : { "name" : "fc_tx_bytes", },
    "rxframes"              : { "name" : "fc_rx_frames", },
    "txframes"              : { "name" : "fc_tx_frames", },
    "link_failures"         : { "name" : "fc_link_fails" },
    "sync_losses"           : { "name" : "fc_sync_losses" },
    "prim_seq_proto_errors" : { "name" : "fc_prim_seq_errors" },
    "invalid_tx_words"      : { "name" : "fc_invalid_tx_words" },
    "discards"              : { "name" : "fc_c2c3_discards" },
    "invalid_crcs"          : { "name" : "fc_invalid_crcs" },
    "address_id_errors"     : { "name" : "fc_address_id_errors" },
    "link_reset_ins"        : { "name" : "fc_link_resets_in" },
    "link_reset_outs"       : { "name" : "fc_link_resets_out" },
    "ols_ins"               : { "name" : "fc_offline_seqs_in" },
    "ols_outs"              : { "name" : "fc_offline_seqs_out" },
    "c2_fbsy_frames"        : { "name" : "fc_c2_fbsy_frames" },
    "c2_frjt_frames"        : { "name" : "fc_c2_frjt_frames" },
}

check_metrics["check_mk-mysql.innodb_io"] = {
    "read" : { "name" : "disk_read_throughput" },
    "write": { "name" : "disk_write_throughput" }
}

check_metrics["check_mk-esx_vsphere_counters.diskio"] = {
    "read"      : { "name" : "disk_read_throughput" },
    "write"     : { "name" : "disk_write_throughput" },
    "ios"       : { "name" : "disk_ios" },
    "latency"   : { "name" : "disk_latency" },
}

check_metrics["check_mk-emcvnx_disks"] = {
    "read" : { "name" : "disk_read_throughput" },
    "write": { "name" : "disk_write_throughput" }
}

check_metrics["check_mk-diskstat"] = {
    "read" : { "name" : "disk_read_throughput" },
    "write": { "name" : "disk_write_throughput" }
}

check_metrics["check_mk-netapp_api_protocol"] = {
    "read_ops" : { "name" : "disk_read_ios" },
    "write_ops": { "name" : "disk_write_ios" }
}

check_metrics["check_mk-ibm_svc_systemstats.iops"] = {
    "read"  : { "name" : "disk_read_ios" },
    "write" : { "name" : "disk_write_ios" }
}

check_metrics["check_mk-dell_powerconnect_temp"] = {
    "temperature" : { "name" : "temp" }
}

check_metrics["check_mk-ipmi_sensors"] = {
    "value" : { "name" : "temp" }
}

check_metrics["check_mk-ipmi"] = {
    "ambient_temp" : { "name" : "temp" }
}

check_metrics["check_mk-wagner_titanus_topsense.smoke"] = {
    "smoke_perc" : { "name" : "smoke_ppm" }
}

check_metrics["check_mk-wagner_titanus_topsense.airflow_deviation"] = {
    "airflow_deviation" : { "name" : "deviation_airflow" }
}

check_metrics["check_mk-wagner_titanus_topsense.chamber_deviation"] = {
    "chamber_deviation" : { "name" : "deviation_calibration_point" }
}

check_metrics["check_mk-apc_symmetra"] = {
    "OutputLoad" : { "name" : "output_load" },
    "batcurr"    : { "name" : "battery_current" },
    "systemp"    : { "name" : "battery_temp" },
    "capacity"   : { "name" : "battery_capacity" },
    "runtime"    : { "name" : "lifetime_remaining", "scale" : 60 },
}

check_metrics["check_mk-kernel.util"]                           = {
    "wait" : { "name" : "io_wait" },
    "guest" : { "name" : "cpu_util_guest" },
    "steal" : { "name" : "cpu_util_steal" },
}

check_metrics["check_mk-lparstat_aix.cpu_util"] = {
    "wait" : { "name" : "io_wait" }
}

check_metrics["check_mk-ucd_cpu_util"] = {
    "wait" : { "name" : "io_wait" }
}

check_metrics["check_mk-vms_cpu"] = {
    "wait" : { "name" : "io_wait" }
}

check_metrics["check_mk-vms_sys.util"] = {
    "wait" : { "name" : "io_wait" }
}

check_metrics["check_mk-winperf.cpuusage"] = {
    "cpuusage" : { "name" : "util" }
}

check_metrics["check_mk-h3c_lanswitch_cpu"] = {
    "usage" : { "name" : "util" }
}

check_metrics["check_mk-h3c_lanswitch_cpu"] = {
    "usage" : { "name" : "util" }
}

check_metrics["check_mk-brocade_mlx.module_cpu"] = {
    "cpu_util1"   : { "name" : "util1s" },
    "cpu_util5"   : { "name" : "util5s" },
    "cpu_util60"  : { "name" : "util1" },
    "cpu_util200" : { "name" : "util5" },
}

check_metrics["check_mk-dell_powerconnect"] = {
    "load"        : { "name" : "util" },
    "loadavg 60s" : { "name" : "util1" },
    "loadavg 5m"  : { "name" : "util5" },
}

check_metrics["check_mk-ibm_svc_nodestats.cache"] = {
    "write_cache_pc" : { "name" : "write_cache_usage" },
    "total_cache_pc" : { "name" : "total_cache_usage" }
}

check_metrics["check_mk-ibm_svc_systemstats.cache"] = {
    "write_cache_pc" : { "name" : "write_cache_usage" },
    "total_cache_pc" : { "name" : "total_cache_usage" }
}

check_metrics["check_mk-esx_vsphere_hostsystem.mem_usage"] = {
    "usage" : { "name" : "mem_used" }
}

check_metrics["check_mk-ibm_svc_host"] = {
    "active"    : { "name" : "hosts_active" },
    "inactive"  : { "name" : "hosts_inactive" },
    "degraded"  : { "name" : "hosts_degraded" },
    "offline"   : { "name" : "hosts_offline" },
    "other"     : { "name" : "hosts_other" },
}

check_metrics["check_mk-juniper_screenos_mem"] = {
    "usage" : { "name" : "mem_used" }
}

check_metrics["check_mk-juniper_trpz_mem"] = {
    "usage" : { "name" : "mem_used" }
}

check_metrics["check_mk-ibm_svc_nodestats.iops"] = {
    "read" : { "name" : "disk_read_ios" },
    "write": { "name" : "disk_write_ios" }
}

check_metrics["check_mk-openvpn_clients"] = {
    "in" : { "name" : "if_in_octets" },
    "out": { "name" : "if_out_octets" }
}

check_metrics["check_mk-f5_bigip_interfaces"] = {
    "bytes_in" : { "name" : "if_in_octets" },
    "bytes_out": { "name" : "if_out_octets" }
}

check_metrics["check_mk-mbg_lantime_state"] = {
    "offset" : { "name" : "time_offset", "scale" : 0.000001 }
} # convert us -> sec

check_metrics["check_mk-mbg_lantime_ng_state"] = {
    "offset" : { "name" : "time_offset", "scale" : 0.000001 }
} # convert us -> sec

check_metrics["check_mk-systemtime"] = {
    "offset" : { "name" : "time_offset" }
}

check_metrics["check_mk-ntp"] = {
    "offset" : { "name" : "time_offset", "scale" : m },
    "jitter" : { "scale" : m },
}
check_metrics["check_mk-chrony"] = {
    "offset" : { "name" : "time_offset", "scale" : m }
}

check_metrics["check_mk-ntp.time"] = {
    "offset" : { "name" : "time_offset", "scale" : m },
    "jitter" : { "scale" : m },
}

check_metrics["check_mk-adva_fsp_if"] = {
    "output_power" : { "name" : "output_signal_power_dbm" },
    "input_power" : { "name" : "input_signal_power_dbm" }
}

check_metrics["check_mk-allnet_ip_sensoric.tension"] = {
    "tension" : { "name" : "voltage_percent" }
}

check_metrics["check_mk-apache_status"] = {
    "Uptime"               : { "name" : "uptime" },
    "IdleWorkers"          : { "name" : "idle_workers" },
    "BusyWorkers"          : { "name" : "busy_workers" },
    "OpenSlots"            : { "name" : "open_slots" },
    "TotalSlots"           : { "name" : "total_slots" },
    "CPULoad"              : { "name" : "load1" },
    "ReqPerSec"            : { "name" : "requests_per_second" },
    "BytesPerSec"          : { "name" : "direkt_io" },
    "ConnsTotal"           : { "name" : "connections" },
    "ConnsAsyncWriting"    : { "name" : "connections_async_writing" },
    "ConnsAsyncKeepAlive"  : { "name" : "connections_async_keepalive" },
    "ConnsAsyncClosing"    : { "name" : "connections_async_closing" },
    "State_StartingUp"     : { "name" : "apache_state_startingup" },
    "State_Waiting"        : { "name" : "apache_state_waiting" },
    "State_Logging"        : { "name" : "apache_state_logging" },
    "State_DNS"            : { "name" : "apache_state_dns" },
    "State_SendingReply"   : { "name" : "apache_state_sending_reply" },
    "State_ReadingRequest" : { "name" : "apache_state_reading_request" },
    "State_Closing"        : { "name" : "apache_state_closing" },
    "State_IdleCleanup"    : { "name" : "apache_state_idle_cleanup" },
    "State_Finishing"      : { "name" : "apache_state_finishing" },
    "State_Keepalive"      : { "name" : "apache_state_keep_alive" },
}

check_metrics["check_mk-ups_socomec_out_voltage"] = {
    "out_voltage" : { "name" : "voltage" }
}

check_metrics["check_mk-hp_blade_psu"] = {
    "output" : { "name" : "power" }
}

check_metrics["check_mk-apc_rackpdu_power"] = {
    "amperage" : { "name" : "current" }
}

check_metrics["check_mk-apc_ats_output"] = {
    "volt" : { "name" : "voltage" },
    "watt" : { "name" : "power"},
    "ampere": { "name": "current"},
    "load_perc" : { "name": "output_load" }
}

check_metrics["check_mk-ups_out_load"] = {
    "out_load"    : { "name": "output_load" },
    "out_voltage" : { "name": "voltage" },
}

check_metrics["check_mk-raritan_pdu_outletcount"] = {
    "outletcount" : { "name" : "connector_outlets" }
}

check_metrics["check_mk-docsis_channels_upstream"] = {
    "total"      : { "name" : "total_modems" },
    "active"     : { "name" : "active_modems" },
    "registered" : { "name" : "registered_modems" },
    "util"       : { "name" : "channel_utilization" },
    "frequency"  : { "scale" : 1000000.0 },
}

check_metrics["check_mk-zfs_arc_cache"]  = {
    "hit_ratio"     : { "name": "cache_hit_ratio", },
    "size"          : { "name": "caches", "scale" : MB },
    "arc_meta_used" : { "name": "zfs_metadata_used", "scale" : MB },
    "arc_meta_limit": { "name": "zfs_metadata_limit", "scale" : MB },
    "arc_meta_max"  : { "name": "zfs_metadata_max", "scale" : MB },
}

check_metrics["check_mk-zfs_arc_cache.l2"] = {
    "l2_size"      : { "name": "zfs_l2_size" },
    "l2_hit_ratio" : { "name": "zfs_l2_hit_ratio", },
}

check_metrics["check_mk-postgres_sessions"] = {
    "total": {"name": "total_sessions"},
    "running": {"name": "running_sessions"}
}

check_metrics["check_mk-oracle_sessions"] = {
    "sessions" : {"name": "running_sessions"}
}

check_metrics["check_mk-oracle_logswitches"] = {
    "logswitches" : { "name" : "logswitches_last_hour" }
}

check_metrics["check_mk-oracle_dataguard_stats"] = {
    "apply_lag" : { "name" : "database_apply_lag" }
}

check_metrics["check_mk-db2_logsize"] = {
    "~[_/]": { "name": "fs_used", "scale" : MB }
}

check_metrics["check_mk-steelhead_connections"] = {
    "active"      : { "name" : "fw_connections_active" },
    "established" : { "name" : "fw_connections_established" },
    "halfOpened"  : { "name" : "fw_connections_halfopened" },
    "halfClosed"  : { "name" : "fw_connections_halfclosed" },
    "passthrough" : { "name" : "fw_connections_passthrough" },
}

check_metrics["check_mk-oracle_tablespaces"] = {
    "size" : { "name" : "tablespace_size" },
    "used" : { "name" : "tablespace_used" },
    "max_size" : { "name" : "tablespace_max_size" },
}

check_metrics["check_mk-mssql_tablespaces"] = {
    "size"          : { "name" : "database_size" },
    "unallocated"   : { "name" : "unallocated_size" },
    "reserved"      : { "name" : "reserved_size" },
    "data"          : { "name" : "data_size" },
    "indexes"       : { "name" : "indexes_size" },
    "unused"        : { "name" : "unused_size" },
}

check_metrics["check_mk-f5_bigip_vserver"] = {
    "conn_rate" : { "name" : "connections_rate" }
}

check_metrics["check_mk-arcserve_backup"] = {
    "size" : { "name" : "backup_size" }
}

check_metrics["check_mk-oracle_rman"] = {
    "age" : { "name" : "backup_age" }
}

check_metrics["check_mk-veeam_client"] = {
    "totalsize" : { "name" : "backup_size" },
    "duration"  : { "name" : "backup_duration" },
    "avgspeed"  : { "name" : "backup_avgspeed" },
}

check_metrics["check_mk-cups_queues"] = {
    "jobs" : { "name" : "printer_queue" }
}

check_metrics["check_mk-printer_pages"] = {
    "pages" : { "name" : "pages_total" }
}

check_metrics["check_mk-livestatus_status"] = {
    "host_checks"    : { "name" : "host_check_rate" },
    "service_checks" : { "name" : "service_check_rate" },
    "connections"    : { "name" : "livestatus_connect_rate" },
    "requests"       : { "name" : "livestatus_request_rate" },
    "log_messages"   : { "name" : "log_message_rate" },
}

check_metrics["check_mk-cisco_wlc_clients"] = {
    "clients" : { "name" : "connections" }
}

check_metrics["check_mk-cisco_qos"] = {
    "drop" : { "name" : "qos_dropped_bytes_rate" },
    "post" : { "name" : "qos_outbound_bytes_rate" },

}

check_metrics["check_mk-hivemanager_devices"] = {
    "clients_count" : { "name" : "connections" }
}

check_metrics["check_mk-ibm_svc_license"] = {
    "licensed" : { "name" : "licenses" }
}

check_metrics["check_mk-tsm_stagingpools"] = {
    "free" : { "name" : "tapes_free" },
    "free" : { "name" : "tapes_total" },
    "util" : { "name" : "tapes_util" }
}

check_metrics["check_mk-hpux_tunables.shmseg"] = {
    "segments" : { "name" : "shared_memory_segments" }
}

check_metrics["check_mk-hpux_tunables.semmns"] = {
    "entries"  : { "name" : "semaphores" }
}

check_metrics["check_mk-hpux_tunables.maxfiles_lim"] = {
    "files" : { "name" : "files_open" }
}

check_metrics["check_mk-win_dhcp_pools"] = {
    "free" : { "name" : "free_dhcp_leases" },
    "used" : { "name" : "used_dhcp_leases" },
    "pending" : { "name" : "pending_dhcp_leases" }
}

check_metrics["check_mk-lparstat_aix"] = {
    "sys" : { "name" : "system" },
    "wait" : { "name" : "io_wait" },
}

check_metrics["check_mk-netapp_fcpio"] = {
    "read"  : { "name" : "disk_read_throughput" },
    "write" : { "name" : "disk_write_throughput" },
}

check_metrics["check_mk-netapp_api_vf_stats.traffic"] = {
    "read_bytes"  : { "name" : "disk_read_throughput" },
    "write_bytes" : { "name" : "disk_write_throughput" },
    "read_ops"    : { "name" : "disk_read_ios" },
    "write_ops"   : { "name" : "disk_write_ios" },
}

check_metrics["check_mk-job"] = {
    "reads"    : { "name" : "disk_read_throughput" },
    "writes"   : { "name" : "disk_write_throughput" },
    "real_time": { "name" : "job_duration" },
}

ps_translation = {
    "count"   : { "name" : "processes" },
    "vsz"     : { "name" : "process_virtual_size", "scale" : KB, },
    "rss"     : { "name" : "process_resident_size", "scale" : KB, },
    "pcpu"    : { "name" : "util" },
    "pcpuavg" : { "name" : "util_average" },
}

check_metrics["check_mk-smart.stats"] = {
    "Power_On_Hours"            : { "name" : "uptime", "scale" : 3600 },
    "Power_Cycle_Count"         : { "name" : "harddrive_power_cycle" },
    "Reallocated_Sector_Ct"     : { "name" : "harddrive_reallocated_sectors" },
    "Reallocated_Event_Count"   : { "name" : "harddrive_reallocated_events" },
    "Spin_Retry_Count"          : { "name" : "harddrive_spin_retries" },
    "Current_Pending_Sector"    : { "name" : "harddrive_pending_sectors" },
    "Command_Timeout"           : { "name" : "harddrive_cmd_timeouts" },
    "End-to-End_Error"          : { "name" : "harddrive_end_to_end_errors" },
    "Reported_Uncorrect"        : { "name" : "harddrive_uncorrectable_errors" },
    "UDMA_CRC_Error_Count"      : { "name" : "harddrive_udma_crc_errors" },
}

check_metrics["check_mk-ps"] = ps_translation
check_metrics["check_mk-ps.perf"] = ps_translation


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
    "segments" : [ "ap_devices_drifted", "ap_devices_not_responding" ],
    "total"    : "ap_devices_total",
})

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
    "metric"     : "job_duration",
    "half_value" : 120.0,
    "exponent"   : 2,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "response_time",
    "half_value" : 10,
    "exponent"   : 4,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "mails_received_time",
    "half_value" : 5,
    "exponent"   : 3,
})

perfometer_info.append({
    "type"       : "linear",
    "segments"  : [ "mem_perm_used"],
    "total"     : "mem_perm_used:max",
})

perfometer_info.append({
    "type"       : "linear",
    "segments"  : [ "mem_heap"],
    "total"     : "mem_heap:max",
})

perfometer_info.append({
    "type"       : "linear",
    "segments"  : [ "mem_nonheap"],
    "total"     : "mem_nonheap:max",
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "pressure",
    "half_value" : 0.5,
    "exponent"   : 2,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "cifs_share_users",
    "half_value" : 10,
    "exponent"   : 2,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "connector_outlets",
    "half_value" : 20,
    "exponent"   : 2,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "licenses",
    "half_value" : 500,
    "exponent"   : 2,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "sync_latency",
    "half_value"    : 5,
    "exponent"      : 2,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "backup_size",
    "half_value"    : 150*GB,
    "exponent"      : 2.0,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "fw_connections_active",
    "half_value"    : 100,
    "exponent"      : 2,
})

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "checkpoint_age",
        "half_value"    : 86400,
        "exponent"      : 2,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "backup_age",
        "half_value"    : 86400,
        "exponent"      : 2,
    }
]))

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "backup_age",
    "half_value"    : 86400,
    "exponent"      : 2,
})

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "read_latency",
        "half_value"    : 5,
        "exponent"      : 2,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "write_latency",
        "half_value"    : 5,
        "exponent"      : 2,
    }
]))

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "logswitches_last_hour",
    "half_value"    : 15,
    "exponent"      : 2,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "database_apply_lag",
    "half_value"    : 2500,
    "exponent"      : 2,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "processes",
    "half_value"    : 100,
    "exponent"      : 2,
})

perfometer_info.append({
    "type"          : "linear",
    "segments"      : [ "total_cache_usage" ],
    "total"         : 100.0,
})

perfometer_info.append(("stacked", [
    {
        "type"       : "logarithmic",
        "metric"     : "mem_heap",
        "half_value" : 100 * MB,
        "exponent"   : 2,
    },
    {
        "type"       : "logarithmic",
        "metric"     : "mem_nonheap",
        "half_value" : 100*MB,
        "exponent"   : 2,
    }
]))

perfometer_info.append(("stacked", [
    {
	    "type"      : "linear",
	    "segments"  : [ "threads_idle" ],
	    "total"     : "threads_idle:max",
	},
    {
	    "type"      : "linear",
	    "segments"  : [ "threads_busy" ],
	    "total"     : "threads_busy:max",
    }
]))

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "rta",
    "half_value"    : 0.1,
    "exponent"      : 4
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "execution_time" ],
    "total"     : 90.0,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "load1",
    "half_value"    : 4.0,
    "exponent"      : 2.0
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "temp",
    "half_value"    : 40.0,
    "exponent"      : 1.2
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "context_switches",
    "half_value"    : 1000.0,
    "exponent"      : 2.0
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "major_page_faults",
    "half_value"    : 1000.0,
    "exponent"      : 2.0
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "process_creations",
    "half_value"    : 1000.0,
    "exponent"      : 2.0
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "threads",
    "half_value"    : 400.0,
    "exponent"      : 2.0
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "user", "system", "idle", "nice" ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "user", "system", "idle", "io_wait" ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "user", "system", "io_wait" ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "fpga_util", ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "util", ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "util1", ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "database_size",
    "half_value"    : GB,
    "exponent"      : 5.0,
})

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

# TODO total = None?
perfometer_info.append(("linear", ( [ "mem_used", "swap_used", "caches", "mem_free", "swap_free" ], None, ("mem_total,mem_used,+,swap_used,/", "ratio"))))

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "mem_used" ],
    "total"     : "mem_total",
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "mem_used(%)" ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "time_offset",
    "half_value"    : 1.0,
    "exponent"      : 10.0,
})

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "tablespace_wasted",
        "half_value"    : 1000000,
        "exponent"      : 2,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "indexspace_wasted",
        "half_value"    : 1000000,
        "exponent"      : 2,
    }
]))

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "running_sessions" ],
    "total"     : "total_sessions",
})

# TODO total : None?
perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "shared_locks", "exclusive_locks" ],
    "total"     : None,
})

perfometer_info.append({
        "type"      : "logarithmic",
        "metric"    : "connections",
        "half_value": 50,
        "exponent"  : 2
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "connection_time",
    "half_value"    : 0.2,
    "exponent"      : 2,
})

perfometer_info.append(("dual", [
    {
        "type"          : "logarithmic",
        "metric"        : "input_signal_power_dbm",
        "half_value"    : 4,
        "exponent"      : 2,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "output_signal_power_dbm",
        "half_value"    : 4,
        "exponent"      : 2,
    }
]))

perfometer_info.append(("dual", [
    {
        "type"          : "logarithmic",
        "metric"        : "read_blocks",
        "half_value"    : 50000000,
        "exponent"      : 2,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "write_blocks",
        "half_value"    : 50000000,
        "exponent"      : 2,
    }
]))

perfometer_info.append({
    "type"      : "logarithmic",
    "metric"    : "running_sessions",
    "half_value": 10,
    "exponent"  : 2
})

perfometer_info.append(("dual", [
    {
        "type"          : "logarithmic",
        "metric"        : "deadlocks",
        "half_value"    : 50,
        "exponent"      : 2,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "lockwaits",
        "half_value"    : 50,
        "exponent"      : 2,
    }
]))


# TODO: max fehlt
perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "sort_overflow" ],
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "mem_used" ],
    "total"     : "mem_used:max",
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "tablespace_used" ],
    "total"     : "tablespace_max_size",
})

perfometer_info.append(("stacked", [
    ("dual", [
        {
            "type"      : "linear",
            "label"     : None,
            "segments"  : [ "total_hitratio" ],
            "total": 100
        },
        {
            "type"      : "linear",
            "label"     : None,
            "segments"  : [ "data_hitratio" ],
            "total"     : 100
        }
    ]),
    ("dual", [
        {
            "type"      : "linear",
            "label"     : None,
            "segments"  : [ "index_hitratio" ],
            "total"     : 100
        },
        {
            "type"      : "linear",
            "label"     : None,
            "segments"  : [ "xda_hitratio" ],
            "total"     : 100
        }
    ])
]))

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "output_load" ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "power",
    "half_value"    : 1000,
    "exponent"      : 2,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "current",
    "half_value"    : 10,
    "exponent"      : 4,
})

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "voltage",
    "half_value"    : 220.0,
    "exponent"      : 2,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "voltage_percent" ],
    "total"     : 100.0,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "humidity" ],
    "total"     : 100.0,
})

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "requests_per_second",
        "half_value"    : 10,
        "exponent"      : 5,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "busy_workers",
        "half_value"    : 10,
        "exponent"      : 2,
    }
]))

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "cache_hit_ratio" ],
    "total"     : 100,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "zfs_l2_hit_ratio" ],
    "total"     : 100,
})

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "signal_noise",
        "half_value"    : 50.0,
        "exponent"      : 2.0,
    },
    {
        "type"          : "linear",
        "segments"      : [ "codewords_corrected", "codewords_uncorrectable" ],
        "total"         : 1.0,
    }
]))

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "signal_noise",
    "half_value"    : 50.0,
    "exponent"      : 2.0
}) # Fallback if no codewords are available

perfometer_info.append(("dual", [
    {
        "type"          : "logarithmic",
        "metric"        : "disk_read_throughput",
        "half_value"    : 5000000,
        "exponent"      : 10,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "disk_write_throughput",
        "half_value"    : 5000000,
        "exponent"      : 10,
    }
]))

perfometer_info.append({
    "type"      : "logarithmic",
    "metric"    : "disk_ios",
    "half_value": 30,
    "exponent"  : 2,
})

perfometer_info.append({
    "type"      : "logarithmic",
    "metric"    : "disk_capacity",
    "half_value": 25*TB,
    "exponent"  : 2,
})

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "printer_queue",
    "half_value" : 10,
    "exponent"   : 2,
})

perfometer_info.append({
    "type"      : "logarithmic",
    "metric"    : "pages_total",
    "half_value": 60000,
    "exponent"  : 2,
})

perfometer_info.append({
    "type"     : "linear",
    "segments" : [ "supply_toner_cyan" ],
    "total"    : 100.0,
})

perfometer_info.append({
    "type"     : "linear",
    "segments" : [ "supply_toner_magenta" ],
    "total"    : 100.0,
})

perfometer_info.append({
    "type"     : "linear",
    "segments" : [ "supply_toner_yellow" ],
    "total"    : 100.0,
})

perfometer_info.append({
    "type"     : "linear",
    "segments" : [ "supply_toner_black" ],
    "total"    : 100.0,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "smoke_ppm" ],
    "total"     : 10,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "deviation_calibration_point" ],
    "total"     : 10,
})

perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "deviation_airflow" ],
    "total"     : 10,
})

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "direct_io",
        "half_value"    : 25,
        "exponent"      : 2,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "buffered_io",
        "half_value"    : 25,
        "expoent"       : 2,
    }
]))

# TODO: :max should be the default?
perfometer_info.append({
    "type"      : "linear",
    "segments"  : [ "used_dhcp_leases" ],
    "total"     : "used_dhcp_leases:max",
})

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "host_check_rate",
        "half_value"    : 50,
        "exponent"      : 5,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "service_check_rate",
        "half_value"    : 200,
        "exponent"      : 5,
    }
]))

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "normal_updates",
        "half_value"    : 10,
        "exponent"      : 2,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "security_updates",
        "hal_value"     : 10,
        "exponent"      : 2,
    }
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

perfometer_info.append(("stacked", [
    {
        "type"          : "logarithmic",
        "metric"        : "mail_queue_deferred_length",
        "half_value"    : 10000,
        "exponent"      : 5,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "mail_queue_active_length",
        "half_value"    : 10000,
        "exponent"      : 5,
    }
]))

perfometer_info.append({
    "type"          : "logarithmic",
    "metric"        : "mail_queue_deferred_length",
    "half_value"    : 10000,
    "exponent"      : 5
})

perfometer_info.append({
    "type"     : "linear",
    "segments" : [ "tapes_util" ],
    "total"    : 100.0,
})

perfometer_info.append(("dual", [
    {
	    "type"      : "linear",
	    "segments"  : [ "qos_dropped_bytes_rate" ],
	    "total"     : "qos_dropped_bytes_rate:max"
    },
    {
	    "type"      : "linear",
	    "segments"  : [ "qos_outbound_bytes_rate" ],
	    "total"     : "qos_outbound_bytes_rate:max"
    }
]))

perfometer_info.append({
    "type"      : "logarithmic",
    "metric"    : "semaphore_ids",
    "half_value": 50,
    "exponent"  : 2,
})

perfometer_info.append({
    "type"      : "logarithmic",
    "metric"    : "segments",
    "half_value": 10,
    "exponent"  : 2,
})

perfometer_info.append({
    "type"      : "logarithmic",
    "metric"    : "semaphores",
    "half_value": 2500,
    "exponent"  : 2,
})

perfometer_info.append(("dual", [
    {
        "type"          : "logarithmic",
        "metric"        : "fc_rx_bytes",
        "half_value"    : 30 * MB,
        "exponent"      : 3,
    },
    {
        "type"          : "logarithmic",
        "metric"        : "fc_tx_bytes",
        "half_value"    : 30 * MB,
        "exponent"      : 3,
    }
]))

perfometer_info.append({
    "type"       : "logarithmic",
    "metric"     : "request_rate",
    "half_value" : 100,
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

# Order of metrics in graph definitions important if you use only 'area':
# The first one must be the bigger one, then descending.
# Example: ('tablespace_size', 'area'),
#          ('tablespace_used', 'area')

graph_info.append({
    "title"   : _("Context switches"),
    "metrics" : [
        ( "vol_context_switches", "area" ),
        ( "invol_context_switches", "stack" ),
    ],
})

graph_info.append({
    "title"   : _("Busy and idle workers"),
    "metrics" : [
        ( "busy_workers", "area" ),
        ( "idle_workers", "stack" ),
    ],
})

graph_info.append({
    "title"   : _("Total and open slots"),
    "metrics" : [
        ( "total_slots", "area" ),
        ( "open_slots", "area" ),
    ],
})

graph_info.append({
    "title"   : _("Connections"),
    "metrics" : [
        ( "connections_async_writing", "area" ),
        ( "connections_async_keepalive", "stack" ),
        ( "connections_async_closing", "stack" ),
        ( "connections", "line" ),
    ],
})

graph_info.append({
    "title"   : _("Apache status"),
    "metrics" : [
        ( "apache_state_startingup", "area" ),
        ( "apache_state_waiting", "stack" ),
        ( "apache_state_logging", "stack" ),
        ( "apache_state_dns", "stack" ),
        ( "apache_state_sending_reply", "stack" ),
        ( "apache_state_reading_request", "stack" ),
        ( "apache_state_closing", "stack" ),
        ( "apache_state_idle_cleanup", "stack" ),
        ( "apache_state_finishing", "stack" ),
        ( "apache_state_keep_alive", "stack" ),
    ],
})

graph_info.append({
    "title"   : _("Battery currencies"),
    "metrics" : [
        ( "battery_current", "area" ),
        ( "current", "stack" ),
    ],
})

graph_info.append({
    "metrics" : [
        ( "battery_capacity", "area" ),
    ],
    "range" : (0,100),
})


graph_info.append({
    "title"   : _("Qos class traffic"),
    "metrics" : [
        ( "qos_outbound_bytes_rate", "area" ),
        ( "qos_dropped_bytes_rate", "-area" ),
    ],
})

graph_info.append({
    "title"   : _("Read and written blocks"),
    "metrics" : [
        ( "read_blocks", "area" ),
        ( "write_blocks","-area" ),
    ],
})


graph_info.append({
    "title"   : _("RMON packets per second"),
    "metrics" : [
        ( "broadcast_packets", "area" ),
        ( "multicast_packets", "stack" ),
        ( "rmon_packets_63", "stack" ),
        ( "rmon_packets_127", "stack" ),
        ( "rmon_packets_255", "stack" ),
        ( "rmon_packets_511", "stack" ),
        ( "rmon_packets_1023", "stack" ),
        ( "rmon_packets_1518", "stack" ),
    ],
})

graph_info.append({
    "title"   : _("Threads"),
    "metrics" : [
        ( "threads", "area" ),
        ( "threads_daemon", "stack" ),
        ( "threads_max", "stack" ),
    ],
})

graph_info.append({
    "title"   : _("Threadpool"),
    "metrics" : [
        ( "threads_busy", "stack" ),
        ( "threads_idle", "stack" ),
    ],
})

graph_info.append({
    "title"   : _("Disk latency"),
    "metrics" : [
        ( "read_latency", "area" ),
        ( "write_latency", "-area" )
    ],
})

graph_info.append({
    "title"   : _("Backup time"),
    "metrics" : [
        ( "checkpoint_age", "area" ),
        ( "backup_age", "stack" )
    ],
})

graph_info.append({
    "title"   : _("NTP time offset"),
    "metrics" : [
        ( "time_offset", "area" ),
        ( "jitter", "line" )
    ],
})

graph_info.append({
    "metrics" : [ ( "total_cache_usage", "area" ) ],
    "range"   : (0, 100),
})

graph_info.append({
    "title"   : _("ZFS meta data"),
    "metrics" : [
        ( "zfs_metadata_max", "area" ),
        ( "zfs_metadata_used", "area" ),
        ( "zfs_metadata_limit", "line" ),
    ],
})

graph_info.append({
    "title"     : _("Cache hit ratio"),
    "metrics"   : [
        ( "cache_hit_ratio", "area" ),
        ( "prefetch_metadata_hit_ratio", "line" ),
        ( "prefetch_data_hit_ratio", "area" ),
    ],
})

graph_info.append({
    "title" : _("Used CPU Time"),
    "metrics" : [
        ( "user_time",            "area" ),
        ( "children_user_time",   "stack" ),
        ( "system_time",          "stack" ),
        ( "children_system_time", "stack" ),
        ( "user_time,children_user_time,system_time,children_system_time,+,+,+#888", "line", _("Total") ),
    ],
})

graph_info.append({
    "title" : _("CPU Time"),
    "metrics" : [
        ( "user_time",            "area" ),
        ( "system_time",          "stack" ),
        ( "user_time,system_time,+", "line", _("Total") ),
    ],
    "conflicting_metrics" : [ "children_user_time" ],
})

graph_info.append({
    "title"   : _("Tapes utilization"),
    "metrics" : [
        ( "tapes_free", "area" ),
        ( "tapes_total", "line" ),
    ],
    "scalars" : [
        "tapes_free:warn",
        "tapes_free:crit",
    ]
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
    ],
    "optional_metrics" : [ "load15" ],
})

graph_info.append({
    "title"   : _( "FGPA utilization" ),
    "metrics" : [
        ( "fpga_util", "area" ),
    ],
    "scalars" : [
        "fpga_util:warn",
        "fpga_util:crit",
    ],
    "range" : (0, 100),
})

graph_info.append({
    "metrics" : [
        ( "util",         "area" ),
        ( "util_average", "line" ),
    ],
    "scalars" : [
        "util:warn",
        "util:crit",
    ],
    "range" : (0, 100),
    "optional_metrics":  [ "util_average" ],
    "conflicting_metrics" : [ "user" ],
})

graph_info.append({
    "title" : _("CPU utilization (%(util:max@count) CPU Threads)"),
    "metrics" : [
        ( "util,user,-#ff6000",  "stack", _("Privileged") ),
        ( "user",                "area" ),
        ( "util#008000",         "line", _("Total") ),
    ],
    "scalars" : [
        "util:warn",
        "util:crit",
    ],
    "range" : (0, 100),
})

graph_info.append({
    "title"   : _( "CPU utilization" ),
    "metrics" : [
        ( "util1", "area" ),
        ( "util15", "line" )
    ],
    "scalars" : [
        "util1:warn",
        "util1:crit",
    ],
    "range" : (0, 100),
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

graph_info.append({
    "title"   : _("CPU utilization"),
    "metrics" : [
        ( "user",                           "area"  ),
        ( "system",                         "stack" ),
        ( "idle",                           "stack" ),
        ( "nice",                           "stack" ),
    ],
    "range" : (0, 100),
})

graph_info.append({
    "title"   : _("CPU utilization"),
    "metrics" : [
        ( "user",                           "area"  ),
        ( "system",                         "stack" ),
        ( "idle",                           "stack" ),
        ( "io_wait",                        "stack" ),
    ],
    "range" : (0, 100),
})

graph_info.append({
    "title"   : _("CPU utilization"),
    "metrics" : [
        ( "user",                           "area"  ),
        ( "system",                         "stack" ),
        ( "io_wait",                        "stack" ),
        ( "user,system,io_wait,+,+#004080", "line", _("Total") ),
    ],
    "conflicting_metrics" : [
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    "mirror_legend" : True,
    "range" : (0, 100),
})

graph_info.append({
    "title"   : _("CPU utilization"),
    "metrics" : [
        ( "user",                           "area"  ),
        ( "system",                         "stack" ),
        ( "io_wait",                        "stack" ),
        ( "cpu_util_guest",                 "stack" ),
        ( "cpu_util_steal",                 "stack" ),
        ( "user,system,io_wait,cpu_util_guest,cpu_util_steal,+,+,+,+#004080", "line", _("Total") ),
    ],
    "omit_zero_metrics" : True,
    "mirror_legend" : True,
    "range" : (0, 100),
})

graph_info.append({
    "title"   : _("CPU utilization"),
    "metrics" : [
        ( "user",                           "area"  ),
        ( "system",                         "stack" ),
        ( "interrupt",                      "stack" ),
    ],
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
    "title": _("Firewall connections"),
    "metrics" : [
        ( "fw_connections_active", "stack" ),
        ( "fw_connections_established", "stack" ),
        ( "fw_connections_halfopened", "stack" ),
        ( "fw_connections_halfclosed", "stack" ),
        ( "fw_connections_passthrough", "stack" ),
    ],
})

graph_info.append({
    "title": _("Time to connect"),
    "metrics" : [
        ( "connection_time", "area" ),
    ],
    "legend_scale" : m,
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
    "title" : _("Disk throughput"),
    "metrics" : [
        ( "disk_read_throughput",  "area" ),
        ( "disk_write_throughput", "-area" ),
    ],
    "legend_scale" : MB,
})

graph_info.append({
    "title" : _("Disk I/O operations"),
    "metrics" : [
        ( "disk_read_ios",  "area" ),
        ( "disk_write_ios", "-area" ),
    ],
})

graph_info.append({
    "title" : _("Direct and buffered I/O operations"),
    "metrics" : [
        ( "direct_io",  "stack" ),
        ( "buffered_io", "stack" ),
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
    "title"   : _( "Spare and broken disks"),
    "metrics" : [
        ( "disks",        "area" ),
        ( "spare_disks",  "stack" ),
        ( "failed_disks", "stack" ),
    ],
})

graph_info.append({
    "title"   : _( "Database sizes" ),
    "metrics" : [
        ( "database_size",  "area" ),
        ( "unallocated_size",  "stack" ),
        ( "reserved_size",  "stack" ),
        ( "data_size",  "stack" ),
        ( "indexes_size",  "stack" ),
        ( "unused_size",  "stack" ),
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

graph_info.append({
    "metrics" : [
        ( "deadlocks",  "area" ),
        ( "lockwaits",  "stack" ),
    ],
})

graph_info.append({
    "metrics" : [
        ( "sort_overflow",  "area" ),
    ],
})

graph_info.append({
    "title"   : _( "Tablespace sizes" ),
    "metrics" : [
        ( "tablespace_size",  "area" ),
        ( "tablespace_used",  "area" ),
    ],
    "scalars" : [
        "tablespace_size:warn",
        "tablespace_size:crit",
    ],
    "range"   : (0, "tablespace_max_size"),
})

# Printer

graph_info.append({
    "metrics" : [
         ( "printer_queue", "area" )
    ],
    "range" : (0, 10),
})

graph_info.append({
    "metrics" : [
         ( "supply_toner_cyan", "area" )
    ],
    "range" : (0, 100),
})

graph_info.append({
    "metrics" : [
         ( "supply_toner_magenta", "area" )
    ],
    "range" : (0, 100),
})

graph_info.append({
    "metrics" : [
         ( "supply_toner_yellow", "area" )
    ],
    "range" : (0, 100),
})

graph_info.append({
    "metrics" : [
         ( "supply_toner_black", "area" )
    ],
    "range" : (0, 100),
})


graph_info.append({
    "title" : _( "Printed pages" ),
    "metrics" : [
        ( "pages_color_a4", "stack" ),
        ( "pages_color_a3", "stack" ),
        ( "pages_bw_a4",    "stack" ),
        ( "pages_bw_a3",    "stack" ),
        ( "pages_total",    "line" ),
    ],
    "optional_metrics" : [
        "pages_color_a4",
        "pages_color_a3",
        "pages_bw_a4",
        "pages_bw_a3",
    ],
    "omit_zero_metrics": True,
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

graph_info.append({
    "title" : _("RAM + Swap used"),
    "metrics" : [
        ("mem_used",  "area"),
        ("swap_used",  "stack"),
        ("mem_total",  "line"),
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
    "conflicting_metrics" : [ "mem_lnx_active_anon" ],
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
        ("mem_lnx_vmalloc_used",  "area"),
        ("mem_lnx_vmalloc_chunk", "stack"),
    ],
})

# TODO: Warum ohne total? Dürfte eigentlich nicht
# vorkommen.
graph_info.append({
    "title" : _("VMalloc Address Space"),
    "metrics" : [
        ("mem_lnx_vmalloc_used", "area"),
        ("mem_lnx_vmalloc_chunk", "stack"),
    ],
})

graph_info.append({
    "title" : _("Heap and non-heap memory"),
    "metrics" : [
        ( "mem_heap",   "area" ),
        ( "mem_nonheap", "stack" ),
    ],
    "conflicting_metrics" : [
        "mem_heap_committed",
        "mem_nonheap_committed",
    ],
})


graph_info.append({
    "title" : _("Heap memory usage"),
    "metrics" : [
        ( "mem_heap_committed", "area" ),
        ( "mem_heap",           "area" ),
    ],
    "scalars" : [
        "mem_heap:warn",
        "mem_heap:crit",
    ]
})

graph_info.append({
    "title" : _("Non-heap memory usage"),
    "metrics" : [
        ( "mem_nonheap_committed", "area" ),
        ( "mem_nonheap",           "area" ),
    ],
    "scalars" : [
        "mem_nonheap:warn",
        "mem_nonheap:crit",
        "mem_nonheap:max",
    ]
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
    "title" : _("Hosts"),
    "metrics" : [
       ( "hosts_active",     "stack"),
       ( "hosts_inactive",   "stack"),
       ( "hosts_degraded",   "stack"),
       ( "hosts_offline",    "stack"),
       ( "hosts_other",      "stack"),
    ],
})

graph_info.append({
    "title" : _("Hosts"),
    "metrics" : [
       ( "hosts_inactive",   "stack"),
       ( "hosts_degraded",   "stack"),
       ( "hosts_offline",    "stack"),
       ( "hosts_other",      "stack"),
    ],
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
    "title" : _("DHCP Leases"),
    "metrics" : [
        ( "used_dhcp_leases",    "area" ),
        ( "free_dhcp_leases",    "stack" ),
        ( "pending_dhcp_leases", "stack" ),
    ],
    "range" : (0, "free_dhcp_leases:max"),
    "scalars" : [
        "free_dhcp_leases:warn",
        "free_dhcp_leases:crit",
    ]
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
    "title" : _("Handled Requests"),
    "metrics" : [
        ("requests_cmk_views",      "stack"),
        ("requests_cmk_wato",       "stack"),
        ("requests_cmk_bi",         "stack"),
        ("requests_cmk_snapins",    "stack"),
        ("requests_cmk_dashboards", "stack"),
        ("requests_cmk_other",      "stack"),
        ("requests_nagvis_snapin",  "stack"),
        ("requests_nagvis_ajax",    "stack"),
        ("requests_nagvis_other",   "stack"),
        ("requests_images",         "stack"),
        ("requests_styles",         "stack"),
        ("requests_scripts",        "stack"),
        ("requests_other",          "stack"),
    ],
    "omit_zero_metrics" : True,
})

graph_info.append({
    "title" : _("Seconds serving"),
    "metrics" : [
        ("secs_cmk_views",      "stack"),
        ("secs_cmk_wato",       "stack"),
        ("secs_cmk_bi",         "stack"),
        ("secs_cmk_snapins",    "stack"),
        ("secs_cmk_dashboards", "stack"),
        ("secs_cmk_other",      "stack"),
        ("secs_nagvis_snapin",  "stack"),
        ("secs_nagvis_ajax",    "stack"),
        ("secs_nagvis_other",   "stack"),
        ("secs_images",         "stack"),
        ("secs_styles",         "stack"),
        ("secs_scripts",        "stack"),
        ("secs_other",          "stack"),
    ],
    "omit_zero_metrics" : True,
})

graph_info.append({
    "title" : _("Bytes sent"),
    "metrics" : [
        ("bytes_cmk_views",      "stack"),
        ("bytes_cmk_wato",       "stack"),
        ("bytes_cmk_bi",         "stack"),
        ("bytes_cmk_snapins",    "stack"),
        ("bytes_cmk_dashboards", "stack"),
        ("bytes_cmk_other",      "stack"),
        ("bytes_nagvis_snapin",  "stack"),
        ("bytes_nagvis_ajax",    "stack"),
        ("bytes_nagvis_other",   "stack"),
        ("bytes_images",         "stack"),
        ("bytes_styles",         "stack"),
        ("bytes_scripts",        "stack"),
        ("bytes_other",          "stack"),
    ],
    "omit_zero_metrics" : True,
})

graph_info.append({
    "title" : _("Outgoing Mails"),
    "metrics" : [
        ( "mail_queue_deferred_length",   "stack" ),
        ( "mail_queue_active_length",     "stack" ),
    ],
})

graph_info.append({
    "title" : _("Modems"),
    "metrics" : [
        ( "active_modems",     "area" ),
        ( "registered_modems", "line" ),
        ( "total_modems",      "line" ),
    ],
})

graph_info.append({
    "title" : _("Net data traffic"),
    "metrics" : [
        ( "net_data_recv",     "stack" ),
        ( "net_data_sent",     "stack" ),
    ],
})

graph_info.append({
    "title" : _("Size of processes"),
    "metrics" : [
        ( "process_resident_size", "area" ),
        ( "process_virtual_size", "stack" ),
    ]
})

graph_info.append({
    "title" : _("Size per process"),
    "metrics" : [
        ( "process_resident_size,processes,/", "area", _("Average resident size per process") ),
        ( "process_virtual_size,processes,/", "stack", _("Average virtual size per process") ),
    ]
})

graph_info.append({
    "title" : _("Throughput"),
    "metrics" : [
        ("fc_tx_bytes", "-area"),
        ("fc_rx_bytes", "area"),
    ],
})

graph_info.append({
    "title" : _("Frames"),
    "metrics" : [
        ("fc_tx_frames", "-area"),
        ("fc_rx_frames", "area"),
    ],
})

graph_info.append({
    "title" : _("Errors"),
    "metrics" : [
        ( "fc_crc_errors", "area" ),
        ( "fc_encouts", "stack" ),
        ( "fc_c3discards", "stack" ),
        ( "fc_notxcredits", "stack" ),
    ]
})

graph_info.append({
    "title" : _("Errors"),
    "metrics" : [
        ( "fc_link_fails", "stack" ),
        ( "fc_sync_losses", "stack" ),
        ( "fc_prim_seq_errors", "stack" ),
        ( "fc_invalid_tx_words", "stack" ),
        ( "fc_invalid_crcs", "stack" ),
        ( "fc_address_id_errors", "stack" ),
        ( "fc_link_resets_in", "stack" ),
        ( "fc_link_resets_out", "stack" ),
        ( "fc_offline_seqs_in", "stack" ),
        ( "fc_offline_seqs_out", "stack" ),
        ( "fc_c2c3_discards", "stack" ),
        ( "fc_c2_fbsy_frames", "stack" ),
        ( "fc_c2_frjt_frames", "stack" ),
    ]
})

graph_info.append({
    "title" : _("NFS traffic"),
    "metrics" : [
        ("nfs_read_data", "-area"),
        ("nfs_write_data", "area"),
    ],
})

graph_info.append({
    "title" : _("NFS latency"),
    "metrics" : [
        ("nfs_read_latency", "-area"),
        ("nfs_write_latency", "area"),
    ],
})

graph_info.append({
    "title" : _("CIFS traffic"),
    "metrics" : [
        ("cifs_read_data", "-area"),
        ("cifs_write_data", "area"),
    ],
})

graph_info.append({
    "title" : _("CIFS latency"),
    "metrics" : [
        ("cifs_read_latency", "-area"),
        ("cifs_write_latency", "area"),
    ],
})

graph_info.append({
    "title" : _("SAN traffic"),
    "metrics" : [
        ("san_read_data", "-area"),
        ("san_write_data", "area"),
    ],
})

graph_info.append({
    "title" : _("SAN latency"),
    "metrics" : [
        ("san_read_latency", "-area"),
        ("san_write_latency", "area"),
    ],
})

graph_info.append({
    "title" : _("FCP traffic"),
    "metrics" : [
        ("fcp_read_data", "-area"),
        ("fcp_write_data", "area"),
    ],
})

graph_info.append({
    "title" : _("FCP latency"),
    "metrics" : [
        ("fcp_read_latency", "-area"),
        ("fcp_write_latency", "area"),
    ],
})

graph_info.append({
    "title" : _("ISCSI traffic"),
    "metrics" : [
        ("icsci_read_data", "-area"),
        ("icsci_write_data", "area"),
    ],
})

graph_info.append({
    "title" : _("ICSCI latency"),
    "metrics" : [
        ("icsci_read_latency", "-area"),
        ("icsci_write_latency", "area"),
    ],
})

graph_info.append({
    "title" : _("Harddrive health statistic"),
    "metrics" : [
        ("harddrive_power_cycle",           "stack"),
        ("harddrive_reallocated_sectors",   "stack"),
        ("harddrive_reallocated_events",    "stack"),
        ("harddrive_spin_retries",          "stack"),
        ("harddrive_pending_sectors",       "stack"),
        ("harddrive_cmd_timeouts",          "stack"),
        ("harddrive_end_to_end_errors",     "stack"),
        ("harddrive_uncorrectable_errors",  "stack"),
        ("harddrive_udma_crc_errors",       "stack"),
    ],
})

graph_info.append({
    "title" : _("Access point statistics"),
    "metrics" : [
        ( "ap_devices_total", "area"),
        ( "ap_devices_drifted", "area"),
        ( "ap_devices_not_responding", "stack"),
    ]
})

