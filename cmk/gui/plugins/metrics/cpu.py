#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._color import indexed_color
from cmk.gui.graphing._utils import graph_info, MAX_CORES, metric_info
from cmk.gui.i18n import _l

# .
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

# TODO: user -> cpu_util_user
metric_info["user"] = {
    "title": _l("User"),
    "help": _l("CPU time spent in user space"),
    "unit": "%",
    "color": "#60f020",
}

# metric_info["cpu_util_privileged"] = {
#     "title" : _l("Privileged"),
#     "help"  : _l("CPU time spent in privileged mode"),
#     "unit"  : "%",
#     "color" : "23/a",
# }

metric_info["nice"] = {
    "title": _l("Nice"),
    "help": _l("CPU time spent in user space for niced processes"),
    "unit": "%",
    "color": "#ff9050",
}

metric_info["interrupt"] = {
    "title": _l("Interrupt"),
    "unit": "%",
    "color": "#ff9050",
}

metric_info["system"] = {
    "title": _l("System"),
    "help": _l("CPU time spent in kernel space"),
    "unit": "%",
    "color": "#ff6000",
}

metric_info["io_wait"] = {
    "title": _l("I/O-wait"),
    "help": _l("CPU time spent waiting for I/O"),
    "unit": "%",
    "color": "#00b0c0",
}

metric_info["cpu_util_guest"] = {
    "title": _l("Guest operating systems"),
    "help": _l("CPU time spent for executing guest operating systems"),
    "unit": "%",
    "color": "12/a",
}

metric_info["cpu_util_steal"] = {
    "title": _l("Steal"),
    "help": _l("CPU time stolen by other operating systems"),
    "unit": "%",
    "color": "16/a",
}

metric_info["idle"] = {
    "title": _l("Idle"),
    "help": _l("CPU idle time"),
    "unit": "%",
    "color": "#805022",
}

metric_info["pci_io_util"] = {
    "title": _l("PCI Express IO utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["generic_util"] = {
    "title": _l("Utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["util"] = {
    "title": _l("CPU utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["engine_cpu_util"] = {
    "title": _l("Engine CPU utilization"),
    "unit": "%",
    "color": "33/a",
}

metric_info["util_numcpu_as_max"] = {
    "title": _l("CPU utilization"),
    "unit": "%",
    "color": "#7fff00",
}

metric_info["util_average"] = {
    "title": _l("CPU utilization (average)"),
    "unit": "%",
    "color": "44/a",
}

metric_info["util1"] = {
    "title": _l("CPU utilization last minute"),
    "unit": "%",
    "color": "#60f020",
}

metric_info["util15"] = {
    "title": _l("CPU utilization last 15 minutes"),
    "unit": "%",
    "color": "#008000",
}

metric_info["util_50"] = {
    "title": _l("CPU utilization (50th percentile)"),
    "unit": "%",
    "color": "#50ff20",
}

metric_info["util_95"] = {
    "title": _l("CPU utilization (95th percentile)"),
    "unit": "%",
    "color": "#600020",
}

metric_info["util_99"] = {
    "title": _l("CPU utilization (99th percentile)"),
    "unit": "%",
    "color": "#60f020",
}


metric_info["cpu_entitlement"] = {
    "title": _l("Entitlement"),
    "unit": "",
    "color": "#77FF77",
}

metric_info["cpu_entitlement_util"] = {
    "title": _l("Physical CPU consumption"),
    "unit": "",
    "color": "#FF0000",
}

for i in range(MAX_CORES):
    # generate different colors for each core.
    # unfortunately there are only 24 colors on our
    # color wheel, times two for two shades each, we
    # can only draw 48 differently colored graphs
    metric_info["cpu_core_util_%d" % i] = {
        "title": _l("Utilization Core %d") % i,
        "unit": "%",
        "color": indexed_color(i, MAX_CORES),
    }
    metric_info["cpu_core_util_average_%d" % i] = {
        "title": _l("Average utilization core %d") % i,
        "unit": "%",
        "color": indexed_color(i, MAX_CORES),
    }

metric_info["cpu_reservation"] = {
    "title": _l("CPU reservation"),
    "unit": "%",
    "color": "13/a",
}

# .
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

#
# CPU UTILIZATION
#

graph_info["util_average_1"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("util", "area"),
        ("util_average", "line"),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "range": (0, "util,100,MAX"),
    "conflicting_metrics": [
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
        "io_wait",
        "user",
        "system",
    ],
}

graph_info["util_average_2"] = {
    "title": _l("CPU utilization"),
    "metrics": [("util1", "area"), ("util15", "line")],
    "scalars": [
        "util1:warn",
        "util1:crit",
    ],
    "range": (0, "util1,util15,100,MAX,MAX"),
}

graph_info["cpu_utilization_numcpus"] = {
    "title": _l("CPU utilization (%(util_numcpu_as_max:max@count) CPU Threads)"),
    "metrics": [
        ("user", "area"),
        ("util_numcpu_as_max,user,-#ff6000", "stack", _l("Privileged")),
        ("util_numcpu_as_max#7fff00", "line", _l("Total")),
    ],
    "scalars": [
        "util_numcpu_as_max:warn",
        "util_numcpu_as_max:crit",
    ],
    "range": (0, 100),
    "optional_metrics": ["user"],
}

graph_info["cpu_utilization_simple"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("util_average", "line"),
        ("util#7fff00", "line", _l("Total")),
    ],
    "conflicting_metrics": [
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
        "io_wait",
    ],
    "range": (0, "util,100,MAX"),
    "optional_metrics": ["util_average"],
}

# TODO which warn,crit?
graph_info["cpu_utilization_3"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("idle", "stack"),
        ("nice", "stack"),
    ],
    "range": (0, "user,system,nice,idle,+,+,+,100,MAX"),
}

# TODO which warn,crit?
graph_info["cpu_utilization_4"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("idle", "stack"),
        ("io_wait", "stack"),
    ],
    "range": (0, "user,system,io_wait,idle,+,+,+,100,MAX"),
}

# The following 8 graphs come in pairs.
# If possible, we display the "util" metric,
# otherwise we display the sum of the present metrics.

# TODO which warn,crit?
graph_info["cpu_utilization_5"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("util_average", "line"),
        ("user,system,io_wait,+,+#7fff00", "line", _l("Total")),
    ],
    "conflicting_metrics": [
        "util",
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    "range": (0, "user,system,io_wait,+,+,100,MAX"),
    "optional_metrics": ["util_average"],
}

graph_info["cpu_utilization_5_util"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("util_average", "line"),
        ("util#7fff00", "line", _l("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": [
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    "range": (0, "util,100,MAX"),
    "optional_metrics": ["util_average"],
}

# TODO which warn,crit?
graph_info["cpu_utilization_6_steal"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_steal", "stack"),
        ("util_average", "line"),
        ("user,system,io_wait,cpu_util_steal,+,+,+#7fff00", "line", _l("Total")),
    ],
    "conflicting_metrics": [
        "util",
        "cpu_util_guest",
    ],
    "omit_zero_metrics": True,
    "range": (0, "user,system,io_wait,cpu_util_steal,+,+,+,100,MAX"),
    "optional_metrics": ["util_average"],
}

graph_info["cpu_utilization_6_steal_util"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_steal", "stack"),
        ("util_average", "line"),
        ("util#7fff00", "line", _l("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": [
        "cpu_util_guest",
    ],
    "omit_zero_metrics": True,
    "range": (0, "util,100,MAX"),
    "optional_metrics": ["util_average"],
}
# TODO which warn,crit?
graph_info["cpu_utilization_6_guest"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("util_average", "line"),
        ("user,system,io_wait,cpu_util_steal,+,+,+#7fff00", "line", _l("Total")),
    ],
    "conflicting_metrics": [
        "util",
    ],
    "omit_zero_metrics": True,
    "range": (0, "user,system,io_wait,cpu_util_steal,+,+,+,100,MAX"),
    "optional_metrics": ["util_average"],
}

graph_info["cpu_utilization_6_guest_util"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("util_average", "line"),
        ("util#7fff00", "line", _l("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": [
        "cpu_util_steal",
    ],
    "omit_zero_metrics": True,
    "range": (0, "util,100,MAX"),
    "optional_metrics": ["util_average"],
}

# TODO which warn,crit?
graph_info["cpu_utilization_7"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("cpu_util_steal", "stack"),
        ("util_average", "line"),
        ("user,system,io_wait,cpu_util_guest,cpu_util_steal,+,+,+,+#7fff00", "line", _l("Total")),
    ],
    "conflicting_metrics": [
        "util",
    ],
    "omit_zero_metrics": True,
    "range": (0, "user,system,io_wait,cpu_util_guest,cpu_util_steal,+,+,+,+,100,MAX"),
    "optional_metrics": ["util_average"],
}

graph_info["cpu_utilization_7_util"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("cpu_util_steal", "stack"),
        ("util_average", "line"),
        ("util#7fff00", "line", _l("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "omit_zero_metrics": True,
    "range": (0, "util,100,MAX"),
    "optional_metrics": ["util_average"],
}

# ^-- last eight graphs go pairwise together (see above)

# TODO which warn,crit?
graph_info["cpu_utilization_8"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("interrupt", "stack"),
    ],
    "range": (0, "util,100,MAX"),
}

graph_info["cpu_utilization_percentile"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("util_50", "line"),
        ("util_95", "line"),
        ("util_99", "line"),
    ],
}

graph_info["util_fallback"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("util", "area"),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": ["util_average", "system", "engine_cpu_util"],
    "range": (0, "util,100,MAX"),
}

graph_info["cpu_entitlement"] = {
    "title": _l("CPU entitlement"),
    "metrics": [("cpu_entitlement", "area"), ("cpu_entitlement_util", "line")],
}

graph_info["per_core_utilization"] = {
    "title": _l("Per Core utilization"),
    "metrics": [("cpu_core_util_%d" % num, "line") for num in range(MAX_CORES)],
    "range": (0, 100),
    "optional_metrics": ["cpu_core_util_%d" % num for num in range(2, MAX_CORES)],
}

graph_info["per_core_utilization_average"] = {
    "title": _l("Average utilization per core"),
    "metrics": [("cpu_core_util_average_%d" % num, "line") for num in range(MAX_CORES)],
    "range": (0, 100),
    "optional_metrics": ["cpu_core_util_average_%d" % num for num in range(2, MAX_CORES)],
}

graph_info["cpu_utilization"] = {
    "title": _l("CPU utilization"),
    "metrics": [
        ("util", "line"),
        ("engine_cpu_util", "line"),
    ],
}
