#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping

import pytest

from cmk.agent_based.v2 import GetRateError, Metric, Result, Service, State, StringTable
from cmk.legacy_checks.sophos_messages import (
    _check_sophos_messages,
    discover_sophos_messages,
    parse_sophos_messages,
)

NOW = 1700000000.0


def _section(inbound: int, outbound: int) -> StringTable:
    return parse_sophos_messages(
        [
            ["Legit", str(inbound), str(outbound)],
            ["Blocked", "10", "0"],
            ["InvalidRecipient", str(inbound), str(outbound)],
        ]
    )


def _warm_up_counters(item: str, value_store: MutableMapping[str, object]) -> None:
    for cycle, (inbound, outbound) in enumerate([(32, 2), (92, 8)]):
        with pytest.raises(GetRateError):
            list(
                _check_sophos_messages(
                    item, _section(inbound, outbound), value_store, NOW + cycle * 60
                )
            )


def test_discover_sophos_messages() -> None:
    assert list(discover_sophos_messages(_section(92, 8))) == [
        Service(item="Legit"),
        Service(item="Blocked"),
        Service(item="Invalid Recipient"),
    ]


def test_check_sophos_messages_reports_from_third_cycle_on() -> None:
    value_store: MutableMapping[str, object] = {}
    _warm_up_counters("Legit", value_store)
    assert list(_check_sophos_messages("Legit", _section(152, 14), value_store, NOW + 120)) == [
        Result(
            state=State.OK,
            summary="1.1 Inbounds and Outbounds/s, 1.0 Inbounds/s, 0.1 Outbounds/s",
        ),
        Metric("messages_inbound", 1.0),
        Metric("messages_outbound", 0.1),
    ]


def test_check_sophos_messages_item_is_renamed() -> None:
    value_store: MutableMapping[str, object] = {}
    _warm_up_counters("Invalid Recipient", value_store)
    assert list(
        _check_sophos_messages("Invalid Recipient", _section(152, 14), value_store, NOW + 120)
    ) == [
        Result(
            state=State.OK,
            summary="1.1 Inbounds and Outbounds/s, 1.0 Inbounds/s, 0.1 Outbounds/s",
        ),
        Metric("messages_inbound", 1.0),
        Metric("messages_outbound", 0.1),
    ]


def test_check_sophos_messages_unknown_item() -> None:
    assert not list(_check_sophos_messages("Not In Section", _section(92, 8), {}, NOW))
