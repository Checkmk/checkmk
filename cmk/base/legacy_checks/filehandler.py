#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Measures total allocated file handles.
# The output displays
#  - the number of allocated file handles
#  - the number of allocatedly used file handles (with the 2.4 kernel); or
#    the number of allocatedly unused file handles (with the 2.6 kernel)
#  - the maximum files handles that can be allocated
#    (can also be found in /proc/sys/fs/file-max)
# Example output of '/proc/sys/fs/file-nr':
# <<<filehandler>>>
# 9376        0        817805


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info, factory_settings

factory_settings["filehandler_default_levels"] = {"levels": (80.0, 90.0)}


def inventory_filehandler(info):
    return [(None, {})]


def check_filehandler(_no_item, params, info):
    allocated, _used_or_unused, maximum = info[0]
    state = 0
    perc = float(allocated) / float(maximum) * 100.0
    infotext = "%.1f%% used (%s of %s file handles)" % (perc, allocated, maximum)
    warn, crit = params["levels"]

    if perc >= crit:
        state = 2
    elif perc >= warn:
        state = 1
    if state > 0:
        infotext += " (warn/crit at %.1f%%/%.1f%%)" % (warn, crit)

    return state, infotext, [("filehandler_perc", perc, warn, crit)]


check_info["filehandler"] = LegacyCheckDefinition(
    check_function=check_filehandler,
    discovery_function=inventory_filehandler,
    service_name="Filehandler",
    default_levels_variable="filehandler_default_levels",
    check_ruleset_name="filehandler",
)
