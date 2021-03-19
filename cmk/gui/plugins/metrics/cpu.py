#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

from cmk.gui.plugins.metrics import (
    metric_info,
    graph_info,
    indexed_color,
    MAX_CORES,
)

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
# Colors: See indexed_color() in cmk/gui/plugins/metrics/utils.py

metric_info["load1"] = {
    "title": _("CPU load average of last minute"),
    "unit": "",
    "color": "34/c",
}

metric_info["load5"] = {
    "title": _("CPU load average of last 5 minutes"),
    "unit": "",
    "color": "#428399",
}

metric_info["load15"] = {
    "title": _("CPU load average of last 15 minutes"),
    "unit": "",
    "color": "#2c5766",
}

metric_info["predict_load15"] = {
    "title": _("Predicted average for 15 minute CPU load"),
    "unit": "",
    "color": "#a0b0c0",
}

metric_info["load_instant"] = {
    "title": _("Instantaneous CPU load"),
    "unit": "",
    "color": "42/a",
}

metric_info["context_switches"] = {
    "title": _("Context switches"),
    "unit": "1/s",
    "color": "#80ff20",
}

metric_info["processes"] = {
    "title": _("Processes"),
    "unit": "count",
    "color": "#8040f0",
}

metric_info["threads"] = {
    "title": _("Threads"),
    "unit": "count",
    "color": "#8040f0",
}

metric_info["thread_usage"] = {
    "title": _("Thread usage"),
    "unit": "%",
    "color": "22/a",
}

metric_info["threads_idle"] = {
    "title": _("Idle threads"),
    "unit": "count",
    "color": "#8040f0",
}

metric_info["threads_rate"] = {
    "title": _("Thread creations per second"),
    "unit": "1/s",
    "color": "44/a",
}

metric_info["threads_daemon"] = {
    "title": _("Daemon threads"),
    "unit": "count",
    "color": "32/a",
}

metric_info["dedup_rate"] = {
    "title": _("Deduplication rate"),
    "unit": "count",
    "color": "12/a",
}

metric_info["threads_max"] = {
    "title": _("Maximum number of threads"),
    "help": _("Maximum number of threads started at any given time during the JVM lifetime"),
    "unit": "count",
    "color": "35/a",
}

metric_info["threads_total"] = {
    "title": _("Number of threads"),
    "unit": "count",
    "color": "41/a",
}

metric_info["threads_busy"] = {
    "title": _("Busy threads"),
    "unit": "count",
    "color": "34/a",
}

metric_info["vol_context_switches"] = {
    "title": _("Voluntary context switches"),
    "help": _("A voluntary context switch occurs when a thread blocks "
              "because it requires a resource that is unavailable"),
    "unit": "count",
    "color": "36/a",
}

metric_info["invol_context_switches"] = {
    "title": _("Involuntary context switches"),
    "help": _("An involuntary context switch takes place when a thread "
              "executes for the duration of its time slice or when the "
              "system identifies a higher-priority thread to run"),
    "unit": "count",
    "color": "45/b",
}

# TODO: user -> cpu_util_user
metric_info["user"] = {
    "title": _("User"),
    "help": _("CPU time spent in user space"),
    "unit": "%",
    "color": "#60f020",
}

# metric_info["cpu_util_privileged"] = {
#     "title" : _("Privileged"),
#     "help"  : _("CPU time spent in privileged mode"),
#     "unit"  : "%",
#     "color" : "23/a",
# }

metric_info["nice"] = {
    "title": _("Nice"),
    "help": _("CPU time spent in user space for niced processes"),
    "unit": "%",
    "color": "#ff9050",
}

metric_info["interrupt"] = {
    "title": _("Interrupt"),
    "unit": "%",
    "color": "#ff9050",
}

metric_info["system"] = {
    "title": _("System"),
    "help": _("CPU time spent in kernel space"),
    "unit": "%",
    "color": "#ff6000",
}

metric_info["io_wait"] = {
    "title": _("I/O-wait"),
    "help": _("CPU time spent waiting for I/O"),
    "unit": "%",
    "color": "#00b0c0",
}

metric_info["cpu_util_guest"] = {
    "title": _("Guest operating systems"),
    "help": _("CPU time spent for executing guest operating systems"),
    "unit": "%",
    "color": "12/a",
}

metric_info["cpu_util_steal"] = {
    "title": _("Steal"),
    "help": _("CPU time stolen by other operating systems"),
    "unit": "%",
    "color": "16/a",
}

metric_info["idle"] = {
    "title": _("Idle"),
    "help": _("CPU idle time"),
    "unit": "%",
    "color": "#805022",
}

metric_info["fpga_util"] = {
    "title": _("FPGA utilization"),
    "unit": "%",
    "color": "#60f020",
}

metric_info["overall_util"] = {
    "title": _("Overall utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["pci_io_util"] = {
    "title": _("PCI Express IO utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["memory_util"] = {
    "title": _("Memory utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["generic_util"] = {
    "title": _("Utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["util"] = {
    "title": _("CPU utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["util_numcpu_as_max"] = {
    "title": _("CPU utilization"),
    "unit": "%",
    "color": "#004080",
}

metric_info["util_average"] = {
    "title": _("CPU utilization (average)"),
    "unit": "%",
    "color": "44/a",
}

metric_info["util1s"] = {
    "title": _("CPU utilization last second"),
    "unit": "%",
    "color": "#50ff20",
}

metric_info["util5s"] = {
    "title": _("CPU utilization last five seconds"),
    "unit": "%",
    "color": "#600020",
}

metric_info["util1"] = {
    "title": _("CPU utilization last minute"),
    "unit": "%",
    "color": "#60f020",
}

metric_info["util5"] = {
    "title": _("CPU utilization last 5 minutes"),
    "unit": "%",
    "color": "#80f040",
}

metric_info["util15"] = {
    "title": _("CPU utilization last 15 minutes"),
    "unit": "%",
    "color": "#9a52bf",
}

metric_info["cpu_entitlement"] = {
    "title": _("Entitlement"),
    "unit": "",
    "color": "#77FF77",
}

metric_info["cpu_entitlement_util"] = {
    "title": _("Physical CPU consumption"),
    "unit": "",
    "color": "#FF0000",
}

for i in range(MAX_CORES):
    # generate different colors for each core.
    # unfortunately there are only 24 colors on our
    # color wheel, times two for two shades each, we
    # can only draw 48 differently colored graphs
    metric_info["cpu_core_util_%d" % i] = {
        "title": _("Utilization Core %d") % (i + 1),
        "unit": "%",
        "color": indexed_color(i, MAX_CORES),
    }
    metric_info["cpu_core_util_average_%d" % i] = {
        "title": _("Average utilization core %d") % (i + 1),
        "unit": "%",
        "color": indexed_color(i, MAX_CORES),
    }

metric_info["cpu_time_percent"] = {
    "title": _("CPU time"),
    "unit": "%",
    "color": "#94b65a",
}

metric_info["system_time"] = {
    "title": _("CPU time in system space"),
    "unit": "s",
    "color": "#ff6000",
}

metric_info["app"] = {
    "title": _("Available physical processors in shared pool"),
    "unit": "count",
    "color": "11/a",
}

metric_info["entc"] = {
    "title": _("Entitled capacity consumed"),
    "unit": "%",
    "color": "12/a",
}

metric_info["lbusy"] = {
    "title": _("Logical processor(s) utilization"),
    "unit": "%",
    "color": "13/a",
}

metric_info["nsp"] = {
    "title": _("Average processor speed"),
    "unit": "%",
    "color": "14/a",
}

metric_info["phint"] = {
    "title": _("Phantom interruptions received"),
    "unit": "count",
    "color": "15/a",
}

metric_info["physc"] = {
    "title": _("Physical processors consumed"),
    "unit": "count",
    "color": "16/a",
}

metric_info["utcyc"] = {
    "title": _("Unaccounted turbo cycles"),
    "unit": "%",
    "color": "21/a",
}

metric_info["vcsw"] = {
    "title": _("Virtual context switches"),
    "unit": "%",
    "color": "22/a",
}

metric_info["job_total"] = {
    "title": _("Total number of jobs"),
    "unit": "count",
    "color": "26/a",
}

metric_info["failed_jobs"] = {
    "title": _("Total number of failed jobs"),
    "unit": "count",
    "color": "11/a",
}

metric_info["zombie_jobs"] = {
    "title": _("Total number of zombie jobs"),
    "unit": "count",
    "color": "16/a",
}

metric_info["cpu_percent"] = {
    "title": _("CPU used"),
    "unit": "%",
    "color": "16/a",
}

metric_info["cpu_total_in_millis"] = {
    "title": _("CPU total in ms"),
    "unit": "1/s",
    "color": "26/a",
}

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

graph_info["used_cpu_time"] = {
    "title": _("Used CPU Time"),
    "metrics": [
        ("user_time", "area"),
        ("children_user_time", "stack"),
        ("system_time", "stack"),
        ("children_system_time", "stack"),
        ("user_time,children_user_time,system_time,children_system_time,+,+,+#888888", "line",
         _("Total")),
    ],
    "omit_zero_metrics": True,
    "conflicting_metrics": ["cmk_time_agent", "cmk_time_snmp", "cmk_time_ds"],
}

graph_info["cmk_cpu_time_by_phase"] = {
    "title": _("Time usage by phase"),
    "metrics": [
        ("user_time,children_user_time,+", "stack", _("CPU time in user space")),
        ("system_time,children_system_time,+", "stack", _("CPU time in operating system")),
        ("cmk_time_agent", "stack"),
        ("cmk_time_snmp", "stack"),
        ("cmk_time_ds", "stack"),
        ("execution_time", "line"),
    ],
    "optional_metrics": ["cmk_time_agent", "cmk_time_snmp", "cmk_time_ds"],
}

graph_info["cpu_time"] = {
    "title": _("CPU Time"),
    "metrics": [
        ("user_time", "area"),
        ("system_time", "stack"),
        ("user_time,system_time,+", "line", _("Total")),
    ],
    "conflicting_metrics": ["children_user_time"],
}

graph_info["tapes_utilization"] = {
    "title": _("Tapes utilization"),
    "metrics": [
        ("tapes_free", "area"),
        ("tapes_total", "line"),
    ],
    "scalars": [
        "tapes_free:warn",
        "tapes_free:crit",
    ]
}

graph_info["storage_processor_utilization"] = {
    "title": _("Storage Processor utilization"),
    "metrics": [("storage_processor_util", "area"),],
    "scalars": [
        "storage_processor_util:warn",
        "storage_processor_util:crit",
    ]
}

graph_info["cpu_load"] = {
    "title": _("CPU Load - %(load1:max@count) CPU Cores"),
    "metrics": [
        ("load1", "area"),
        ("load5", "line"),
        ("load15", "line"),
    ],
    "scalars": [
        "load1:warn",
        "load1:crit",
    ],
    "optional_metrics": [
        "load5",
        "load15",
    ],
}

graph_info["fgpa_utilization"] = {
    "title": _("FGPA utilization"),
    "metrics": [("fpga_util", "area"),],
    "scalars": [
        "fpga_util:warn",
        "fpga_util:crit",
    ],
    "range": (0, 100),
}

#
# CPU UTILIZATION
#

graph_info["util_average_1"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("util", "area"),
        ("util_average", "line"),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "range": (0, 100),
}

graph_info["util_average_2"] = {
    "title": _("CPU utilization"),
    "metrics": [("util1", "area"), ("util15", "line")],
    "scalars": [
        "util1:warn",
        "util1:crit",
    ],
    "range": (0, 100),
}

graph_info["cpu_utilization_numcpus"] = {
    "title": _("CPU utilization (%(util_numcpu_as_max:max@count) CPU Threads)"),
    "metrics": [
        ("user", "area"),
        ("util_numcpu_as_max,user,-#ff6000", "stack", _("Privileged")),
        ("util_numcpu_as_max#004080", "line", _("Total")),
    ],
    "scalars": [
        "util_numcpu_as_max:warn",
        "util_numcpu_as_max:crit",
    ],
    "range": (0, 100),
    "optional_metrics": ["user"],
}

graph_info["cpu_utilization_simple"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "conflicting_metrics": [
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
        "io_wait",
    ],
    "range": (0, 100),
}

#TODO which warn,crit?
graph_info["cpu_utilization_3"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("idle", "stack"),
        ("nice", "stack"),
    ],
    "range": (0, 100),
}

#TODO which warn,crit?
graph_info["cpu_utilization_4"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("idle", "stack"),
        ("io_wait", "stack"),
    ],
    "range": (0, 100),
}

# The following 8 graphs come in pairs.
# If possible, we display the "util" metric,
# otherwise we display the sum of the present metrics.

#TODO which warn,crit?
graph_info["cpu_utilization_5"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("user,system,io_wait,+,+#004080", "line", _("Total")),
    ],
    "conflicting_metrics": [
        "util",
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    "range": (0, 100),
}

graph_info["cpu_utilization_5_util"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": [
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    "range": (0, 100),
}

#TODO which warn,crit?
graph_info["cpu_utilization_6_steal"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_steal", "stack"),
        ("user,system,io_wait,cpu_util_steal,+,+,+#004080", "line", _("Total")),
    ],
    "conflicting_metrics": [
        "util",
        "cpu_util_guest",
    ],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

graph_info["cpu_utilization_6_steal_util"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_steal", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": ["cpu_util_guest",],
    "omit_zero_metrics": True,
    "range": (0, 100),
}
#TODO which warn,crit?
graph_info["cpu_utilization_6_guest"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("user,system,io_wait,cpu_util_steal,+,+,+#004080", "line", _("Total")),
    ],
    "conflicting_metrics": [
        "util",
        "cpu_util_steal",
    ],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

graph_info["cpu_utilization_6_guest_util"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": ["cpu_util_steal",],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

#TODO which warn,crit?
graph_info["cpu_utilization_7"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("cpu_util_steal", "stack"),
        ("user,system,io_wait,cpu_util_guest,cpu_util_steal,+,+,+,+#004080", "line", _("Total")),
    ],
    "conflicting_metrics": ["util",],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

graph_info["cpu_utilization_7_util"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("cpu_util_steal", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

# ^-- last eight graphs go pairwise together (see above)

#TODO which warn,crit?
graph_info["cpu_utilization_8"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("interrupt", "stack"),
    ],
    "range": (0, 100),
}

graph_info["util_fallback"] = {
    "title": _("CPU utilization"),
    "metrics": [("util", "area"),],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": [
        "util_average",
        "system",
    ],
    "range": (0, 100),
}

graph_info["cpu_entitlement"] = {
    "title": _("CPU entitlement"),
    "metrics": [("cpu_entitlement", "area"), ("cpu_entitlement_util", "line")],
}

graph_info["per_core_utilization"] = {
    "title": _("Per Core utilization"),
    "metrics": [("cpu_core_util_%d" % num, "line") for num in range(MAX_CORES)],
    "range": (0, 100),
    "optional_metrics": ["cpu_core_util_%d" % num for num in range(2, MAX_CORES)]
}

graph_info["per_core_utilization_average"] = {
    "title": _("Average utilization per core"),
    "metrics": [("cpu_core_util_average_%d" % num, "line") for num in range(MAX_CORES)],
    "range": (0, 100),
    "optional_metrics": ["cpu_core_util_average_%d" % num for num in range(2, MAX_CORES)],
}

graph_info["context_switches"] = {
    "title": _("Context switches"),
    "metrics": [
        ("vol_context_switches", "area"),
        ("invol_context_switches", "stack"),
    ],
}

graph_info["threads"] = {
    "title": _("Threads"),
    "metrics": [
        ("threads", "area"),
        ("threads_daemon", "stack"),
        ("threads_max", "stack"),
    ],
}

graph_info["thread_usage"] = {
    "title": _("Thread usage"),
    "metrics": [("thread_usage", "area"),],
    "scalars": ["thread_usage:warn", "thread_usage:crit"],
    "range": (0, 100),
}

graph_info["threadpool"] = {
    "title": _("Threadpool"),
    "metrics": [
        ("threads_busy", "stack"),
        ("threads_idle", "stack"),
    ],
}
