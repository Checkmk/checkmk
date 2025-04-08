#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.netscaler.agent_based.netscaler_ha import (
    check_netscaler_ha,
    discover_netscaler_ha,
    Health,
    HighAvailabilityMode,
    parse_netscaler_ha,
    Section,
)


def test_parse_netscaler_ha() -> None:
    assert parse_netscaler_ha([["1", "2", "3"]]) == Section(
        our_ha_mode=HighAvailabilityMode.PRIMARY,
        peer_ha_mode=HighAvailabilityMode.SECONDARY,
        our_health=Health.FUNCTIONAL,
    )


def test_discover_netscaler_ha_in_ha_mode() -> None:
    assert list(
        discover_netscaler_ha(
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.SECONDARY,
                our_health=Health.FUNCTIONAL,
            )
        )
    ) == [Service()]


def test_discover_netscaler_ha_in_standalone_mode() -> None:
    assert (
        list(
            discover_netscaler_ha(
                Section(
                    our_ha_mode=HighAvailabilityMode.STANDALONE,
                    peer_ha_mode=HighAvailabilityMode.UNKNOWN,
                    our_health=Health.UNKOWN,
                )
            )
        )
        == []
    )


def test_check_netscaler_ha_default() -> None:
    assert list(
        check_netscaler_ha(
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.SECONDARY,
                our_health=Health.FUNCTIONAL,
            )
        )
    ) == [
        Result(state=State.OK, summary="Failover mode: primary"),
        Result(state=State.OK, summary="Peer failover mode: secondary"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_unknown_failover_mode() -> None:
    assert list(
        check_netscaler_ha(
            Section(
                our_ha_mode=HighAvailabilityMode.UNKNOWN,
                peer_ha_mode=HighAvailabilityMode.SECONDARY,
                our_health=Health.UNKOWN,
            )
        )
    ) == [
        Result(state=State.UNKNOWN, summary="Failover mode: unknown"),
        Result(state=State.OK, summary="Peer failover mode: secondary"),
        Result(state=State.WARN, summary="Health: unknown"),
    ]


def test_check_netscaler_ha_broken() -> None:
    assert list(
        check_netscaler_ha(
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.UNKNOWN,
                our_health=Health.DOWN,
            )
        )
    ) == [
        Result(state=State.OK, summary="Failover mode: primary"),
        Result(state=State.WARN, summary="Peer failover mode: unknown"),
        Result(state=State.CRIT, summary="Health: down"),
    ]


def test_check_netscaler_ha_peer_standalone() -> None:
    assert list(
        check_netscaler_ha(
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.STANDALONE,
                our_health=Health.FUNCTIONAL,
            )
        )
    ) == [
        Result(state=State.OK, summary="Failover mode: primary"),
        Result(state=State.WARN, summary="Peer is in standalone mode"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_peer_unknown() -> None:
    assert list(
        check_netscaler_ha(
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.UNKNOWN,
                our_health=Health.FUNCTIONAL,
            )
        )
    ) == [
        Result(state=State.OK, summary="Failover mode: primary"),
        Result(state=State.WARN, summary="Peer failover mode: unknown"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_standalone() -> None:
    assert not list(
        check_netscaler_ha(
            Section(
                our_ha_mode=HighAvailabilityMode.STANDALONE,
                peer_ha_mode=HighAvailabilityMode.UNKNOWN,
                our_health=Health.UNKOWN,
            )
        )
    )
