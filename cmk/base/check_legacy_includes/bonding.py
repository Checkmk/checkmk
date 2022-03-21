#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Iterable, Mapping

from cmk.base.plugins.agent_based.utils import bonding

DiscoveryResult = Iterable[tuple[str, dict[str, Any]]]
CheckResult = Iterable[tuple[int, str]]


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
    [('bond0', {'primary': 'eth2'})]
    """
    yield from (
        (bond_name, _discovery_params(bond))
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
            yield (
                params["ieee_302_3ad_agg_id_missmatch_state"],
                f"Mismatching aggregator ID of {eth}: {slave_id}",
            )


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
    (0, 'Status: up')
    (0, 'Mode: fault-tolerance')
    (0, 'Primary: eth2')
    (0, 'eth2/f8:4f:57:72:11:34 up')
    (1, 'eth3/f8:4f:57:72:11:36 down')
    """
    if (properties := section.get(item)) is None:
        return

    status = properties["status"]
    yield (
        {"up": 0, "degraded": 1}.get(status, 2),
        f"Status: {status}",
    )
    if status not in {"up", "degraded"}:
        return

    mode = properties["mode"]
    yield 0, "Mode: %s" % mode
    if "IEEE 802.3ad" in mode:
        yield from _check_ieee_302_3ad_specific(params, properties)

    if (speed := properties.get("speed")) is not None:
        yield 0, f"Speed: {speed}"

    current_primary = properties.get("primary", "None")
    primary = current_primary if current_primary != "None" else params.get("primary", "None")
    if primary != "None":
        yield 0, f"Primary: {primary}"

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
            state = 0 if slave["status"] == "up" else 1
            if "hwaddr" in slave:
                yield state, f"{eth}/{slave['hwaddr']} {slave['status']}"
            else:
                yield state, f"{eth} {slave['status']}"
    elif expected_active == active_if:
        yield 0, f"Active: {active_if}"
    else:
        yield 1, f"Active: {active_if} (expected is {expected_active})"


BONDING_CHECK_DEFAULT_PARAMETERS = {
    "ieee_302_3ad_agg_id_missmatch_state": 1,
    "expect_active": "ignore",
}
