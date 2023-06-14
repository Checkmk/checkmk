#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_cisco_fru_module_status(parsed):
    for module_index in parsed:
        yield (module_index, None)


def check_cisco_fru_module_status(item, _no_params, parsed):
    return (
        None
        if not (module := parsed.get(item))
        else (
            module.monitoring_state.value,
            f"{f'[{module.name}] ' if module.name else ''}Operational status: {module.human_readable_state}",
        )
    )


check_info["cisco_fru_module_status"] = LegacyCheckDefinition(
    discovery_function=inventory_cisco_fru_module_status,
    check_function=check_cisco_fru_module_status,
    service_name="FRU Module Status %s",
)
