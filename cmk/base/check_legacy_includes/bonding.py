#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
BONDING_CHECK_DEFAULT_PARAMETERS = {
    'ieee_302_3ad_agg_id_missmatch_state': 1,
    'expect_active': 'ignore',
}


def inventory_bonding(parsed):
    inventory = []
    for bond, status in parsed.items():
        if status["status"] in ("up", "degraded"):
            # If no information about primary interface is available
            # then assume currently active one as primary
            if "primary" not in status and "active" in status:
                params = {"primary": status["active"]}
            else:
                params = {}
            inventory.append((bond, params))
    return inventory


def _check_ieee_302_3ad_specific(params, status):
    master_id = status.get('aggregator_id')
    missmatch_state = params['ieee_302_3ad_agg_id_missmatch_state']

    for eth, slave in status["interfaces"].items():
        slave_id = slave['aggregator_id']
        if master_id is None:
            master_id = slave_id
        if slave_id != master_id:
            yield missmatch_state, "Missmatching aggregator ID of %s: %s" % (eth, slave_id)


def check_bonding(item, params, parsed):
    status = parsed.get(item)
    if not status:
        return

    if status["status"] not in ("up", "degraded"):
        yield 2, "Interface is " + status["status"]
        return

    mode = status["mode"]
    yield 0, "Mode: %s" % mode
    if "IEEE 802.3ad" in mode:
        for result in _check_ieee_302_3ad_specific(params, status):
            yield result

    speed = status.get('speed')
    if speed:
        yield 0, "Speed: %s" % speed

    for eth, slave in status["interfaces"].items():
        state = int(slave["status"] != 'up')
        if "hwaddr" in slave:
            yield state, "%s/%s %s" % (eth, slave["hwaddr"], slave["status"])
        else:
            yield state, "%s %s" % (eth, slave["status"])

    primary = status.get("primary", params.get("primary"))
    if primary:
        yield 0, "Primary: %s" % primary

    active = status.get("active")
    if active:
        state = 0
        info = "Active: %s" % active

        expected_active = None
        expect = params["expect_active"]

        if expect == "primary":
            expected_active = primary
        elif expect == "lowest":
            expected_active = min(status["interfaces"])

        if expected_active is not None and expected_active != active:
            state = 1
            info += " (expected is %s)" % expected_active

        yield state, info

    yield 0 if status["status"] == "up" else 1, "Bond status: %s" % status["status"]
