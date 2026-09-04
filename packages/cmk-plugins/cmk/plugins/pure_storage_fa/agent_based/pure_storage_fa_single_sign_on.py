#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


class SingleSignOn(BaseModel, frozen=True):
    single_sign_on_enabled: bool


def parse_admins_settings(string_table: StringTable) -> SingleSignOn | None:
    json_data = json.loads(string_table[0][0])
    if "items" not in json_data:
        return None
    return SingleSignOn(
        single_sign_on_enabled=json_data["items"][0]["single_sign_on_enabled"],
    )


agent_section_pure_storage_fa_admins_settings = AgentSection(
    name="pure_storage_fa_admins_settings",
    parse_function=parse_admins_settings,
)


def discover_single_sign_on(section: SingleSignOn) -> DiscoveryResult:
    yield Service(parameters={"discovered_state": section.single_sign_on_enabled})


def check_single_sign_on(params, section: SingleSignOn) -> CheckResult:
    data = section.single_sign_on_enabled
    state = State.CRIT
    summary = "Could not find enough data"
    if params["discovered_state"] is data:
        if data:
            state = State.OK
            summary = "SSO Enabled"
        else:
            state = State.OK
            summary = "SSO disabled! (Discovered State)"
    else:
        if data:
            state = State.OK
            summary = "SSO Status changed to 'Enabled'!"
        else:
            state = State.WARN
            summary = "SSO Status changed to 'Disabled'!"

    yield Result(state=state, summary=summary)


check_plugin_pure_storage_fa_single_sign_on = CheckPlugin(
    name="pure_storage_fa_single_sign_on",
    sections=["pure_storage_fa_admins_settings"],
    service_name="Single-Sign-On",
    discovery_function=discover_single_sign_on,
    check_function=check_single_sign_on,
    check_default_parameters={
        "discovered_state": True,
    },
)
