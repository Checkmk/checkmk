#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Agent output examples:# #   .

# Pre-V15 agent output:

# <<<suseconnect:sep(58)>>>
# identifier: SLES
# version: 12.1
# arch: x86_64
# status: Registered
# regcode: banana001
# starts_at: 2015-12-01 00:00:00 UTC
# expires_at: 2019-12-31 00:00:00 UTC
# subscription_status: ACTIVE
# _type: full

# V15+ agent output

# <<<suseconnect:sep(58)>>>
# Installed Products:

#   advanced Systems Management Module
#   (sle-module-adv-systems-management/12/x86_64)

#   Registered

#   sUSE Linux Enterprise Server for SAP Applications 12 SP5
#   (SLES_SAP/12.5/x86_64)

#   Registered

#     Subscription:

#     Regcode: banana005
#     Starts at: 2018-07-01 00:00:00 UTC
#     Expires at: 2021-06-30 00:00:00 UTC
#     Status: ACTIVE
#     Type: full

#   SUSE Package Hub 12
#   (PackageHub/12.5/x86_64)


import time
from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.collection.agent_based.suseconnect import get_data, Section

check_info = {}


def inventory_suseconnect(section: Section) -> Iterable[tuple[None, dict]]:
    if get_data(section) is not None:
        yield None, {}


def check_suseconnect(
    _no_item: str, params: Mapping[str, Any], section: Section
) -> Iterable[tuple[int, str]]:
    # we assume here that the parsed data contains all required keys

    if (specs := get_data(section)) is None:
        return

    state, infotext = 0, "Status: %(registration_status)s" % specs
    if params["status"] != "Ignore" and params["status"] != specs["registration_status"]:
        state = 2
    yield state, infotext

    state, infotext = 0, "Subscription: %(subscription_status)s" % specs
    if (
        params["subscription_status"] != "Ignore"
        and params["subscription_status"] != specs["subscription_status"]
    ):
        state = 2
    yield state, infotext

    yield (
        0,
        (
            "Subscription type: %(subscription_type)s, Registration code: %(registration_code)s, "
            "Starts at: %(starts_at)s, Expires at: %(expires_at)s"
        )
        % specs,
    )

    expiration_date = time.strptime(specs["expires_at"], "%Y-%m-%d %H:%M:%S %Z")
    expiration_time = time.mktime(expiration_date) - time.time()

    if expiration_time > 0:
        warn, crit = params["days_left"]
        days2seconds = 24 * 60 * 60

        if expiration_time <= crit * days2seconds:
            state = 2
        elif expiration_time <= warn * days2seconds:
            state = 1
        else:
            state = 0

        infotext = "Expires in: %s" % render.timespan(expiration_time)
        if state:
            infotext += " (warn/crit at %d/%d days)" % (warn, crit)

        yield state, infotext
    else:
        yield 2, "Expired since: %s" % render.timespan(-1.0 * expiration_time)


check_info["suseconnect"] = LegacyCheckDefinition(
    name="suseconnect",
    service_name="SLES license",
    # section is migrated already!,
    discovery_function=inventory_suseconnect,
    check_function=check_suseconnect,
    check_ruleset_name="sles_license",
    check_default_parameters={
        "status": "Registered",
        "subscription_status": "ACTIVE",
        "days_left": (14, 7),
    },
)
