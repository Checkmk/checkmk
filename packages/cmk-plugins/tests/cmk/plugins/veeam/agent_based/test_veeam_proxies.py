#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_proxies import (
    check_veeam_proxies,
    CheckParameters,
    discovery_veeam_proxies,
    parse_veeam_proxies,
    VeeamProxy,
)

PARAMS = CheckParameters(disabled_state=1)


def _proxy(name: str = "proxy-1", **overrides: object) -> str:
    proxy_dict: dict[str, object] = {
        "id": "id-1",
        "description": "Primary proxy",
        "name": name,
        "type": "ViProxy",
        "hostId": "host-id-1",
        "hostName": "proxy-host-1",
        "isDisabled": False,
        "isOnline": True,
        "isOutOfDate": False,
    }
    proxy_dict.update(overrides)
    return json.dumps(proxy_dict)


def test_discovery_veeam_proxies() -> None:
    section = parse_veeam_proxies([[_proxy("proxy-1")], [_proxy("proxy-2")]])
    assert list(discovery_veeam_proxies(section)) == [
        Service(item="proxy-1"),
        Service(item="proxy-2"),
    ]


def test_parse_veeam_proxies() -> None:
    section = parse_veeam_proxies([[_proxy("proxy-1")]])
    assert section == {
        "proxy-1": VeeamProxy(
            type="ViProxy",
            description="Primary proxy",
            host_name="proxy-host-1",
            is_disabled=False,
            is_online=True,
            is_out_of_date=False,
        )
    }


def test_check_veeam_proxies_online_is_ok() -> None:
    section = parse_veeam_proxies([[_proxy()]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="VMware, Online")


def test_check_veeam_proxies_type_falls_back_to_raw_value_when_unrecognized() -> None:
    section = parse_veeam_proxies([[_proxy(type="SomeFutureType")]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="SomeFutureType, Online")


def test_check_veeam_proxies_offline_is_crit() -> None:
    section = parse_veeam_proxies([[_proxy(isOnline=False)]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    assert results[0] == Result(state=State.CRIT, summary="VMware, Offline")


def test_check_veeam_proxies_out_of_date_is_warn() -> None:
    section = parse_veeam_proxies([[_proxy(isOutOfDate=True)]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    assert results[0] == Result(state=State.WARN, summary="VMware, Online, Out of date")


def test_check_veeam_proxies_disabled_is_warn_by_default() -> None:
    section = parse_veeam_proxies([[_proxy(isDisabled=True)]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    assert results[0] == Result(state=State.WARN, summary="VMware, Online, Disabled")


def test_check_veeam_proxies_disabled_state_is_configurable() -> None:
    params = CheckParameters(disabled_state=0)
    section = parse_veeam_proxies([[_proxy(isDisabled=True)]])
    results = list(check_veeam_proxies("proxy-1", params, section))
    assert results[0] == Result(state=State.OK, summary="VMware, Online, Disabled")


def test_check_veeam_proxies_disabled_and_offline_uses_disabled_state_not_crit() -> None:
    section = parse_veeam_proxies([[_proxy(isOnline=False, isDisabled=True)]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    # A deliberately disabled proxy is normally also offline; the offline check
    # must not force CRIT regardless of the configured disabled_state.
    assert results[0] == Result(state=State.WARN, summary="VMware, Offline, Disabled")


def test_check_veeam_proxies_disabled_and_offline_can_be_silenced() -> None:
    params = CheckParameters(disabled_state=0)
    section = parse_veeam_proxies([[_proxy(isOnline=False, isDisabled=True)]])
    results = list(check_veeam_proxies("proxy-1", params, section))
    assert results[0] == Result(state=State.OK, summary="VMware, Offline, Disabled")


def test_check_veeam_proxies_offline_and_enabled_is_still_crit() -> None:
    section = parse_veeam_proxies([[_proxy(isOnline=False, isDisabled=False)]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    assert results[0] == Result(state=State.CRIT, summary="VMware, Offline")


def test_check_veeam_proxies_details() -> None:
    section = parse_veeam_proxies([[_proxy()]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    assert Result(state=State.OK, notice="Description: Primary proxy") in results
    assert Result(state=State.OK, notice="Host: proxy-host-1") in results


def test_check_veeam_proxies_empty_description_shows_none() -> None:
    section = parse_veeam_proxies([[_proxy(description="")]])
    results = list(check_veeam_proxies("proxy-1", PARAMS, section))
    assert Result(state=State.OK, notice="Description: none") in results


def test_check_veeam_proxies_vanished_item_yields_nothing() -> None:
    section = parse_veeam_proxies([[_proxy("proxy-1")]])
    assert list(check_veeam_proxies("proxy-2", PARAMS, section)) == []
