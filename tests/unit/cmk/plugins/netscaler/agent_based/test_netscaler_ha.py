#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.netscaler_ha import check_netscaler_ha, inventory_netscaler_ha

from cmk.plugins.netscaler.agent_based.netscaler_ha import parse_netscaler_ha, Section


def test_parse_netscaler_ha() -> None:
    assert parse_netscaler_ha([["1", "1", "3"]]) == Section(
        peer_state=1,
        current_status=1,
        current_state=3,
    )


def test_inventory_netscaler_ha() -> None:
    assert inventory_netscaler_ha(
        Section(
            peer_state=1,
            current_status=1,
            current_state=3,
        )
    ) == [(None, None)]


def test_check_netscaler_ha_with_ha() -> None:
    assert check_netscaler_ha(
        None,
        None,
        Section(
            peer_state=1,
            current_status=1,
            current_state=3,
        ),
    ) == (
        0,
        "State: functional, Neighbour: primary",
    )


def test_check_netscaler_ha_without_ha() -> None:
    assert check_netscaler_ha(
        None,
        None,
        Section(
            peer_state=0,
            current_status=0,
            current_state=3,
        ),
    ) == (
        0,
        "System not setup for HA",
    )
