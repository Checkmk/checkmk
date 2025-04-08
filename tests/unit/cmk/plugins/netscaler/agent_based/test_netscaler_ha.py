#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.netscaler.agent_based.netscaler_ha import (
    check_netscaler_ha,
    CheckParams,
    discover_netscaler_ha,
    DiscoveredParams,
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
    ) == [
        Service(
            parameters=DiscoveredParams(discovered_failover_mode="primary"),
        )
    ]


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
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("disabled", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.SECONDARY,
                our_health=Health.FUNCTIONAL,
            ),
        ),
    ) == [
        Result(state=State.OK, summary="Failover mode: primary"),
        Result(state=State.OK, summary="Peer failover mode: secondary"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_unknown_failover_mode() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("explicit_failover_mode", "primary"),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.UNKNOWN,
                peer_ha_mode=HighAvailabilityMode.SECONDARY,
                our_health=Health.UNKOWN,
            ),
        )
    ) == [
        Result(state=State.UNKNOWN, summary="Failover mode: unknown"),
        Result(state=State.OK, summary="Peer failover mode: secondary"),
        Result(state=State.WARN, summary="Health: unknown"),
    ]


def test_check_netscaler_ha_broken() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("disabled", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.UNKNOWN,
                our_health=Health.DOWN,
            ),
        )
    ) == [
        Result(state=State.OK, summary="Failover mode: primary"),
        Result(state=State.WARN, summary="Peer failover mode: unknown"),
        Result(state=State.CRIT, summary="Health: down"),
    ]


def test_check_netscaler_ha_peer_standalone() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("disabled", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.STANDALONE,
                our_health=Health.FUNCTIONAL,
            ),
        )
    ) == [
        Result(state=State.OK, summary="Failover mode: primary"),
        Result(state=State.WARN, summary="Peer is in standalone mode"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_peer_unknown() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("disabled", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.UNKNOWN,
                our_health=Health.FUNCTIONAL,
            ),
        )
    ) == [
        Result(state=State.OK, summary="Failover mode: primary"),
        Result(state=State.WARN, summary="Peer failover mode: unknown"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_ignore_failover() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("disabled", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.SECONDARY,
                peer_ha_mode=HighAvailabilityMode.PRIMARY,
                our_health=Health.FUNCTIONAL,
            ),
        ),
    ) == [
        Result(state=State.OK, summary="Failover mode: secondary"),
        Result(state=State.OK, summary="Peer failover mode: primary"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_discovered_failover_state() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("use_discovered_failover_mode", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.SECONDARY,
                peer_ha_mode=HighAvailabilityMode.PRIMARY,
                our_health=Health.FUNCTIONAL,
            ),
        ),
    ) == [
        Result(state=State.CRIT, summary="Failover mode: secondary, failover detected"),
        Result(state=State.OK, summary="Peer failover mode: primary"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_discovered_failover_state_unknown() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="unknown",
                failover_monitoring=("use_discovered_failover_mode", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.SECONDARY,
                our_health=Health.FUNCTIONAL,
            ),
        ),
    ) == [
        Result(
            state=State.UNKNOWN,
            summary="Failover monitoring is configured to use the discovered failover mode, "
            "but the failover mode was unknown when the last discovery ran. Please re-discover.",
        ),
        Result(state=State.OK, summary="Peer failover mode: secondary"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_discovered_failover_state_missing() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                failover_monitoring=("use_discovered_failover_mode", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.PRIMARY,
                peer_ha_mode=HighAvailabilityMode.SECONDARY,
                our_health=Health.FUNCTIONAL,
            ),
        ),
    ) == [
        Result(
            state=State.UNKNOWN,
            summary="Failover monitoring is configured to use the discovered failover mode, "
            "but no discovered failover mode is available. Please re-discover.",
        ),
        Result(state=State.OK, summary="Peer failover mode: secondary"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_explicit_failover_state() -> None:
    assert list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("explicit_failover_mode", "primary"),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.SECONDARY,
                peer_ha_mode=HighAvailabilityMode.PRIMARY,
                our_health=Health.FUNCTIONAL,
            ),
        ),
    ) == [
        Result(state=State.CRIT, summary="Failover mode: secondary, expected: primary"),
        Result(state=State.OK, summary="Peer failover mode: primary"),
        Result(state=State.OK, summary="Health: functional"),
    ]


def test_check_netscaler_ha_standalone() -> None:
    assert not list(
        check_netscaler_ha(
            CheckParams(
                discovered_failover_mode="primary",
                failover_monitoring=("disabled", None),
            ),
            Section(
                our_ha_mode=HighAvailabilityMode.STANDALONE,
                peer_ha_mode=HighAvailabilityMode.UNKNOWN,
                our_health=Health.UNKOWN,
            ),
        )
    )
