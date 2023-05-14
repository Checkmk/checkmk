#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.checkpoint import DETECT

# FIXME
# The WATO group 'memory_simple' needs an item and the service_description should
# have a '%s'.  At the moment the current item 'System' and 'Memory' without '%s'
# works but is not consistent.  This will be fixed in the future.
# If we change this we loose history and parameter sets have to be adapted.

# comNET GmbH, Fabian Binder

# .1.3.6.1.4.1.2620.1.6.7.4.3.0 8101654528 --> CHECKPOINT-MIB::memTotalReal
# .1.3.6.1.4.1.2620.1.6.7.4.4.0 2091094016 --> CHECKPOINT-MIB::memAvailReal

factory_settings["checkpoint_memory_default_levels"] = {"levels": ("perc_used", (80.0, 90.0))}


def inventory_checkpoint_memory(info):
    if info and len(info[0]) > 1:
        return [("System", {})]
    return []


def check_checkpoint_memory(item, params, info):
    if isinstance(params, tuple):
        params = {"levels": ("perc_used", params)}

    mem_total_bytes, mem_used_bytes = map(int, info[0])
    return check_memory_element(
        "Usage",
        mem_used_bytes,
        mem_total_bytes,
        params.get("levels"),
        metric_name="memory_used",
    )


check_info["checkpoint_memory"] = LegacyCheckDefinition(
    detect=DETECT,
    discovery_function=inventory_checkpoint_memory,
    check_function=check_checkpoint_memory,
    service_name="Memory",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.4",
        oids=["3", "4"],
    ),
    default_levels_variable="checkpoint_memory_default_levels",
    check_ruleset_name="memory_simple",
)
