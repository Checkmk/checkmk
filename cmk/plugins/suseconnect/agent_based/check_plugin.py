#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.suseconnect.agent_based.agent_section import get_data, Section


def discover(section: Section) -> DiscoveryResult:
    if get_data(section) is not None:
        yield Service()


def check(params: Mapping[str, Any], section: Section) -> CheckResult:
    # we assume here that the parsed data contains all required keys

    if (specs := get_data(section)) is None:
        return

    if "registration_status" in specs:
        state, infotext = State.OK, "Status: %s" % specs["registration_status"]
        if params["status"] != "Ignore" and params["status"] != specs["registration_status"]:
            state = State.CRIT
        yield Result(state=state, summary=infotext)

    if "subscription_status" in specs:
        state, infotext = State.OK, "Subscription: %s" % specs["subscription_status"]
        if (
            params["subscription_status"] != "Ignore"
            and params["subscription_status"] != specs["subscription_status"]
        ):
            state = State.CRIT
        yield Result(state=state, summary=infotext)

    if (
        "subscription_type" in specs
        and "registration_code" in specs
        and "starts_at" in specs
        and "expires_at" in specs
    ):
        yield Result(
            state=State.OK,
            summary=(
                "Subscription type: %(subscription_type)s, Registration code: %(registration_code)s, "
                "Starts at: %(starts_at)s, Expires at: %(expires_at)s"
            )
            % specs,
        )

        expiration_date = time.strptime(specs["expires_at"], "%Y-%m-%d %H:%M:%S %Z")
        expiration_time = time.mktime(expiration_date) - time.time()

        if expiration_time > 0:
            yield from check_levels(
                expiration_time,
                levels_lower=params["days_left"],
                label="Expires in",
                render_func=render.timespan,
            )
        else:
            yield Result(
                state=State.CRIT,
                summary="Expired since: %s" % render.timespan(-1.0 * expiration_time),
            )


check_plugin_suseconnect = CheckPlugin(
    name="suseconnect",
    service_name="SLES license",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="sles_license",
    check_default_parameters={
        "status": "Registered",
        "subscription_status": "ACTIVE",
        "days_left": ("fixed", (14.0, 7.0)),
    },
)
