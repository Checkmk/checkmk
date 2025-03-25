#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, TypedDict

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.lib import bonding

DEFAULT_PARAMS = {
    "ieee_302_3ad_agg_id_missmatch_state": 1,
    "expect_active": "ignore",
    "expected_interfaces": {"expected_number": 2, "state": 0},
}


def _discovery_params(bond: bonding.Bond) -> dict[str, str]:
    if bond.get("primary", "None") == "None" and (active := bond.get("active", "None")) != "None":
        return {"primary": active}
    return {}


def discover_bonding(section: bonding.Section) -> DiscoveryResult:
    """Return bonds together with params containing the active interface as primary one in case
    there is no primary interface configured.
    >>> list(discover_bonding({
    ...     'bond0': {
    ...         'status': 'up',
    ...         'mode': 'fault-tolerance',
    ...         'interfaces': {
    ...             'eth2': {'status': 'up', 'hwaddr': 'aa:bb:cc:dd:ee:ff', 'failures': 1},
    ...             'eth3': {'status': 'down', 'hwaddr': '11:22:33:44:55:66', 'failures': 0}},
    ...         'active': 'eth2',
    ...         'primary': 'None',
    ...     },
    ... }))
    [Service(item='bond0', parameters={'primary': 'eth2'})]
    """
    yield from (
        Service(item=bond_name, parameters=_discovery_params(bond))
        for bond_name, bond in section.items()
        if bond["status"] in {"up", "degraded"}
    )


def _check_ieee_302_3ad_specific(params: Mapping[str, Any], status: bonding.Bond) -> CheckResult:
    master_id = status.get("aggregator_id")

    for eth, slave in status["interfaces"].items():
        slave_id = slave["aggregator_id"]
        if master_id is None:
            master_id = slave_id
        if slave_id != master_id:
            yield Result(
                state=State(params["ieee_302_3ad_agg_id_missmatch_state"]),
                summary=f"Mismatching aggregator ID of {eth}: {slave_id}",
            )


mode_map = {
    "mode_0": "round-robin",
    "mode_1": "active-backup",
    "mode_2": "xor",
    "mode_3": "broadcast",
    "mode_4": "802.3ad",
    "mode_5": "transmit",
    "mode_6": "adaptive",
}


class BondingModeConfig(TypedDict):
    mode_0: int
    mode_1: int
    mode_2: int
    mode_3: int
    mode_4: int
    mode_5: int
    mode_6: int


def _check_bonding_mode(current_mode: str, config: BondingModeConfig) -> CheckResult:
    state = State.OK
    summary = f"Mode: {current_mode}"
    for mode, mode_str in mode_map.items():
        if mode_str in current_mode.lower():
            summary = f"Mode: {mode_str}"
            state = State(config[mode])  # type: ignore[literal-required]
            if state != State.OK:
                summary += " (not allowed)"
            break

    yield Result(state=state, summary=summary)


def check_bonding(item: str, params: Mapping[str, Any], section: bonding.Section) -> CheckResult:
    """
    >>> for result in check_bonding(
    ...     "bond0", {
    ...        'ieee_302_3ad_agg_id_missmatch_state': 1,
    ...        'expect_active': 'ignore',
    ...        'primary': 'eth2'},
    ...     {'bond0': {
    ...         'status': 'up',
    ...         'mode': 'fault-tolerance',
    ...         'interfaces': {
    ...             'eth2': {'status': 'up', 'hwaddr': 'f8:4f:57:72:11:34', 'failures': 1},
    ...             'eth3': {'status': 'down', 'hwaddr': 'f8:4f:57:72:11:36', 'failures': 0}},
    ...         'active': 'eth2',
    ...         'primary': 'None'}}):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Status: up')
    Result(state=<State.OK: 0>, summary='Mode: fault-tolerance')
    Result(state=<State.OK: 0>, summary='Primary: eth2')
    Result(state=<State.OK: 0>, summary='eth2/f8:4f:57:72:11:34 up')
    Result(state=<State.WARN: 1>, summary='eth3/f8:4f:57:72:11:36 down')
    """

    if (properties := section.get(item)) is None:
        return

    status = properties["status"]
    yield Result(
        state={"up": State.OK, "degraded": State.WARN}.get(status, State.CRIT),
        summary=f"Status: {status}",
    )
    if status not in {"up", "degraded"}:
        return

    mode = properties["mode"]
    if params.get("bonding_mode_states") is not None:
        config: BondingModeConfig = params["bonding_mode_states"]
        yield from _check_bonding_mode(mode, config)
    else:
        yield Result(state=State.OK, summary=f"Mode: {mode}")

    if "IEEE 802.3ad" in mode:
        yield from _check_ieee_302_3ad_specific(params, properties)

    if (speed := properties.get("speed")) is not None:
        yield Result(state=State.OK, summary=f"Speed: {speed}")

    current_primary = properties.get("primary", "None")
    primary = current_primary if current_primary != "None" else params.get("primary", "None")
    if primary != "None":
        yield Result(state=State.OK, summary=f"Primary: {primary}")

    expected_active = {
        "primary": primary,
        "lowest": min(properties["interfaces"]),
        "ignore": None,
    }.get(params["expect_active"])

    active_if = properties.get("active", "None")
    if expected_active is None:
        # we don't expect an interface to be up and others to be down so check whether all
        # interfaces are up
        for eth, slave in properties["interfaces"].items():
            state = State.OK if slave["status"] == "up" else State.WARN
            if "hwaddr" in slave:
                yield Result(state=state, summary=f"{eth}/{slave['hwaddr']} {slave['status']}")
            else:
                yield Result(state=state, summary=f"{eth} {slave['status']}")
    elif expected_active == active_if:
        yield Result(state=State.OK, summary=f"Active: {active_if}")
    else:
        yield Result(
            state=State.WARN, summary=f"Active: {active_if} (expected is {expected_active})"
        )

    if (number_interfaces := params.get("expected_interfaces")) is not None:
        if (actual_number := len(properties["interfaces"])) < number_interfaces["expected_number"]:
            yield Result(
                state=State(number_interfaces["state"]),
                summary=f"Unexpected number of interfaces (expected: {number_interfaces['expected_number']}, got: {actual_number})",
            )


check_plugin_bonding = CheckPlugin(
    name="bonding",
    service_name="Bonding Interface %s",
    discovery_function=discover_bonding,
    check_function=check_bonding,
    check_ruleset_name="bonding",
    check_default_parameters=DEFAULT_PARAMS,
)

check_plugin_ovs_bonding = CheckPlugin(
    name="ovs_bonding",
    service_name="OVS Bonding interface %s",
    discovery_function=discover_bonding,
    check_function=check_bonding,
    check_ruleset_name="ovs_bonding",
    check_default_parameters=DEFAULT_PARAMS,
)


def never_discover(section: bonding.Section) -> DiscoveryResult:
    yield from ()


check_plugin_windows_intel_bonding = CheckPlugin(
    name="windows_intel_bonding",
    # unfortunately, this one is written with lower 'i' :-(
    service_name="Bonding interface %s",
    # This plug-in is not discovered since version 2.2
    discovery_function=never_discover,
    check_function=check_bonding,
    check_ruleset_name="bonding",
    check_default_parameters=DEFAULT_PARAMS,
)
