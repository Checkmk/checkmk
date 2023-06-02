#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<citrix_controller>>>
# ControllerState Active
# ControllerVersion 7.6.0.5024
# DesktopsRegistered 29
# LicensingServerState OK
# LicensingGraceState NotActive
# ActiveSiteServices RZ2XenPool01 - Cisco UCS VMware
# TotalFarmActiveSessions 262
# TotalFarmInactiveSessions 14

#   .--Active Site Services------------------------------------------------.
#   |               _        _   _             ____  _ _                   |
#   |              / \   ___| |_(_)_   _____  / ___|(_) |_ ___             |
#   |             / _ \ / __| __| \ \ / / _ \ \___ \| | __/ _ \            |
#   |            / ___ \ (__| |_| |\ V /  __/  ___) | | ||  __/            |
#   |           /_/   \_\___|\__|_| \_/ \___| |____/|_|\__\___|            |
#   |                                                                      |
#   |                ____                  _                               |
#   |               / ___|  ___ _ ____   _(_) ___ ___  ___                 |
#   |               \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|                |
#   |                ___) |  __/ |   \ V /| | (_|  __/\__ \                |
#   |               |____/ \___|_|    \_/ |_|\___\___||___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api import v1


def inventory_citrix_controller_services(info):
    for line in info:
        if line[0] == "ActiveSiteServices":
            yield v1.Service()
            return


def check_citrix_controller_services(_no_item, _no_params, info):
    for line in info:
        if line[0] == "ActiveSiteServices":
            yield v1.Result(state=v1.State.OK, summary=" ".join(line[1:]) or "No services")
            return


check_info["citrix_controller.services"] = LegacyCheckDefinition(
    discovery_function=inventory_citrix_controller_services,
    check_function=check_citrix_controller_services,
    service_name="Citrix Active Site Services",
)

# .
#   .--Desktops Registered-------------------------------------------------.
#   |               ____            _    _                                 |
#   |              |  _ \  ___  ___| | _| |_ ___  _ __  ___                |
#   |              | | | |/ _ \/ __| |/ / __/ _ \| '_ \/ __|               |
#   |              | |_| |  __/\__ \   <| || (_) | |_) \__ \               |
#   |              |____/ \___||___/_|\_\\__\___/| .__/|___/               |
#   |                                            |_|                       |
#   |            ____            _     _                    _              |
#   |           |  _ \ ___  __ _(_)___| |_ ___ _ __ ___  __| |             |
#   |           | |_) / _ \/ _` | / __| __/ _ \ '__/ _ \/ _` |             |
#   |           |  _ <  __/ (_| | \__ \ ||  __/ | |  __/ (_| |             |
#   |           |_| \_\___|\__, |_|___/\__\___|_|  \___|\__,_|             |
#   |                      |___/                                           |
#   '----------------------------------------------------------------------'


def inventory_citrix_controller_registered(info):
    for line in info:
        if line[0] == "DesktopsRegistered":
            yield v1.Service()
    return []


def check_citrix_controller_registered(_no_item, params, info):
    for line in info:
        if line[0] == "DesktopsRegistered":
            try:
                count_desktops = int(line[1])
            except (IndexError, ValueError):
                # Is UNKNOWN right behaviour?
                yield v1.Result(state=v1.State.UNKNOWN, summary="No desktops registered")
                return

            levels = params.get("levels", (None, None)) + params.get("levels_lower", (None, None))

            state, message, metrics = check_levels(
                count_desktops, "registered_desktops", levels, human_readable_func=int
            )
            metric = metrics[0]
            yield v1.Result(state=v1.State(state), summary=message)
            yield v1.Metric(
                value=metric[1], name=metric[0], levels=params.get("levels", (None, None))
            )
            return


check_info["citrix_controller.registered"] = LegacyCheckDefinition(
    discovery_function=inventory_citrix_controller_registered,
    check_function=check_citrix_controller_registered,
    service_name="Citrix Desktops Registered",
    check_ruleset_name="citrix_desktops_registered",
)
