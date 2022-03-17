#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file

BONDING_CHECK_DEFAULT_PARAMETERS = {
    "ieee_302_3ad_agg_id_missmatch_state": 1,
    "expect_active": "ignore",
}


def inventory_bonding(parsed):
    """Return bonds together with params containing the active interface as primary one in case
    there is no primary interface configured.
    >>> inventory_bonding({'bond0': {
    ...     'status': 'up',
    ...     'mode': 'fault-tolerance',
    ...     'interfaces': {
    ...         'eth2': {'status': 'up', 'hwaddr': 'aa:bb:cc:dd:ee:ff', 'failures': 1},
    ...         'eth3': {'status': 'down', 'hwaddr': '11:22:33:44:55:66', 'failures': 0}},
    ...     'active': 'eth2',
    ...     'primary': 'None'}})
    [('bond0', {'primary': 'eth2'})]
    """
    return [
        (bond, params)  #
        for bond, props in parsed.items()  #
        if props["status"] in {"up", "degraded"}  #
        for primary, active in ((props.get("primary", "None"), props.get("active", "None")),)  #
        for params in ({} if primary != "None" or active == "None" else {"primary": active},)
    ]


def _check_ieee_302_3ad_specific(params, status):
    master_id = status.get("aggregator_id")
    mismatch_state = params["ieee_302_3ad_agg_id_missmatch_state"]

    for eth, slave in status["interfaces"].items():
        slave_id = slave["aggregator_id"]
        if master_id is None:
            master_id = slave_id
        if slave_id != master_id:
            yield mismatch_state, "Mismatching aggregator ID of %s: %s" % (eth, slave_id)


def check_bonding(item, params, parsed):
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
    (0, 'Mode: fault-tolerance')
    (0, 'Primary: eth2')
    (0, 'eth2/f8:4f:57:72:11:34 up')
    (1, 'eth3/f8:4f:57:72:11:36 down')
    (0, 'Bond status: up')
    """
    properties = parsed.get(item)
    if not properties:
        return  # => status: UNKN

    if properties["status"] not in {"up", "degraded"}:
        yield 2, "Interface is " + properties["status"]
        return

    mode = properties["mode"]
    yield 0, "Mode: %s" % mode
    if "IEEE 802.3ad" in mode:
        yield from _check_ieee_302_3ad_specific(params, properties)

    speed = properties.get("speed")
    if speed:
        yield 0, "Speed: %s" % speed

    current_primary = properties.get("primary", "None")
    primary = current_primary if current_primary != "None" else params.get("primary", "None")
    if primary != "None":
        yield 0, "Primary: %s" % primary

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
                yield state, "%s/%s %s" % (eth, slave["hwaddr"], slave["status"])
            else:
                yield state, "%s %s" % (eth, slave["status"])
    elif expected_active == active_if:
        yield 0, "Active: %s" % active_if
    else:
        yield 1, "Active: %s (expected is %s)" % (active_if, expected_active)

    yield 0 if properties["status"] == "up" else 1, "Bond status: %s" % properties["status"]
