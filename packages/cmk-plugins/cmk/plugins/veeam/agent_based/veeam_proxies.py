#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TypedDict

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


class ProxyType(StrEnum):
    VI_PROXY = "ViProxy"
    HV_PROXY = "HvProxy"
    GENERAL_PURPOSE_PROXY = "GeneralPurposeProxy"


@dataclass(frozen=True, kw_only=True)
class VeeamProxy:
    """Mirrors the VBR REST API's ProxyStateModel
    (GET /api/v1/backupInfrastructure/proxies/states)."""

    type: ProxyType | str
    description: str
    host_name: str
    is_disabled: bool
    is_online: bool
    is_out_of_date: bool


Section = Mapping[str, VeeamProxy]


class CheckParameters(TypedDict):
    disabled_state: int


DEFAULT_PARAMETERS = CheckParameters(disabled_state=State.OK.value)


def parse_veeam_proxies(string_table: StringTable) -> Section:
    section: dict[str, VeeamProxy] = {}
    for line in string_table:
        proxy_dict = json.loads(line[0])
        section[proxy_dict["name"]] = VeeamProxy(
            type=_parse_type(proxy_dict["type"]),
            description=proxy_dict["description"],
            host_name=proxy_dict["hostName"],
            is_disabled=proxy_dict["isDisabled"],
            is_online=proxy_dict["isOnline"],
            is_out_of_date=proxy_dict["isOutOfDate"],
        )
    return section


def discovery_veeam_proxies(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _parse_type(raw_type: str) -> ProxyType | str:
    try:
        return ProxyType(raw_type)
    except ValueError:
        return raw_type


def _known_type_display_name(type_: ProxyType) -> str:
    match type_:
        case ProxyType.VI_PROXY:
            return "VMware vSphere"
        case ProxyType.HV_PROXY:
            return "Hyper-V"
        case ProxyType.GENERAL_PURPOSE_PROXY:
            return "General purpose"


def _type_display_name(type_: ProxyType | str) -> str:
    return _known_type_display_name(type_) if isinstance(type_, ProxyType) else type_


def check_veeam_proxies(item: str, params: CheckParameters, section: Section) -> CheckResult:
    if (proxy := section.get(item)) is None:
        return

    state_words = ["Online" if proxy.is_online else "Offline"]
    if proxy.is_disabled:
        state_words.append("Disabled")
    if proxy.is_out_of_date:
        state_words.append("Out of date")

    # A deliberately disabled proxy is normally also offline; only let "offline"
    # escalate to CRIT when the proxy isn't disabled, so disabled_state remains
    # in control of the overall state for a disabled proxy.
    online_state = State.OK if proxy.is_disabled or proxy.is_online else State.CRIT
    overall_state = State.worst(
        online_state,
        State.WARN if proxy.is_out_of_date else State.OK,
        State(params["disabled_state"]) if proxy.is_disabled else State.OK,
    )
    yield Result(
        state=overall_state,
        summary=f"{_type_display_name(proxy.type)}, {', '.join(state_words)}",
    )

    yield Result(
        state=State.OK,
        notice=f"Description: {proxy.description}" if proxy.description else "Description: none",
    )
    yield Result(
        state=State.OK,
        notice=f"Host: {proxy.host_name}",
    )


agent_section_veeam_proxies = AgentSection(
    name="veeam_proxies",
    parse_function=parse_veeam_proxies,
)

check_plugin_veeam_proxies = CheckPlugin(
    name="veeam_proxies",
    service_name="Backup proxy %s",
    discovery_function=discovery_veeam_proxies,
    check_function=check_veeam_proxies,
    check_ruleset_name="veeam_proxies",
    check_default_parameters=DEFAULT_PARAMETERS,
)
