#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.netapp.agent_based.netapp_ontap_time import (
    check_netapp_ontap_time,
    discover_netapp_ontap_time,
    parse_netapp_ontap_time_status,
)
from cmk.plugins.netapp.models import NtpPeerStatusModel, NtpStatusModel


class NtpPeerStatusModelFactory(ModelFactory[NtpPeerStatusModel]):
    __model__ = NtpPeerStatusModel


class NtpStatusModelFactory(ModelFactory[NtpStatusModel]):
    __model__ = NtpStatusModel


def test_parse_netapp_ontap_time_status() -> None:
    string_table = [
        [
            '{"node":"Node 1","peers":[{"server":"ntp-1","offset":-1.35,"is_peer_selected":true},{"server":"ntp-2","offset":-0.65,"is_peer_selected":false}]}'
        ],
        ['{"node":"Node 2","peers":[]}'],
    ]

    result = parse_netapp_ontap_time_status(string_table)

    assert result == {
        "Node 1": NtpStatusModel(
            node="Node 1",
            peers=[
                NtpPeerStatusModel(server="ntp-1", offset=-1.35, is_peer_selected=True),
                NtpPeerStatusModel(server="ntp-2", offset=-0.65, is_peer_selected=False),
            ],
        ),
        "Node 2": NtpStatusModel(node="Node 2", peers=[]),
    }


def test_discover_netapp_ontap_time() -> None:
    ntp_section: Mapping[str, NtpStatusModel] = {
        "Node 1": NtpStatusModelFactory.build(
            node="Node 1",
            peers=[
                NtpPeerStatusModelFactory.build(
                    server="ntp-1",
                    offset=-1.35,
                    is_peer_selected=True,
                ),
            ],
        ),
        "Node 2": NtpStatusModelFactory.build(
            node="Node 2",
            peers=[],
        ),
    }

    result = list(discover_netapp_ontap_time(ntp_section))

    assert result == [
        Service(item="Node 1"),
        Service(item="Node 2"),
    ]


def test_check_netapp_ontap_time_ok() -> None:
    ntp_section: Mapping[str, NtpStatusModel] = {
        "Node 1": NtpStatusModelFactory.build(
            node="Node 1",
            peers=[
                NtpPeerStatusModelFactory.build(
                    server="ntp-1",
                    offset=-1.35,
                    is_peer_selected=True,
                ),
                NtpPeerStatusModelFactory.build(
                    server="ntp-2",
                    offset=-0.65,
                    is_peer_selected=False,
                ),
            ],
        ),
    }

    result = list(
        check_netapp_ontap_time(
            "Node 1",
            {"offset": ("fixed", (0.001, 0.002))},
            ntp_section,
        )
    )

    assert result == [
        Result(state=State.OK, notice="Selected NTP server: ntp-1"),
        Result(
            state=State.WARN,
            summary="Offset: 1 millisecond (warn/crit at 1 millisecond/2 milliseconds)",
        ),
        Metric("time_offset", 0.00135, levels=(0.001, 0.002)),
    ]


@pytest.mark.parametrize(
    ("item", "ntp_section", "expected"),
    [
        pytest.param(
            "Node 1",
            {
                "Node 1": NtpStatusModelFactory.build(
                    node="Node 1",
                    peers=[
                        NtpPeerStatusModelFactory.build(
                            server="ntp-1",
                            offset=-1.35,
                            is_peer_selected=False,
                        ),
                        NtpPeerStatusModelFactory.build(
                            server="ntp-2",
                            offset=-0.65,
                            is_peer_selected=False,
                        ),
                    ],
                ),
            },
            [
                Result(state=State.CRIT, summary="No selected NTP server found"),
            ],
            id="crit-if-no-selected-peer-for-node",
        ),
        pytest.param(
            "Node 1",
            {
                "Node 1": NtpStatusModelFactory.build(
                    node="Node 1",
                    peers=[
                        NtpPeerStatusModelFactory.build(
                            server="ntp-1",
                            offset=None,
                            is_peer_selected=True,
                        ),
                    ],
                ),
            },
            [
                Result(state=State.CRIT, summary="Selected NTP server provided no offset"),
            ],
            id="crit-if-selected-peer-has-no-offset",
        ),
        pytest.param(
            "Node 1",
            {
                "Node 1": NtpStatusModelFactory.build(
                    node="Node 1",
                    peers=[],
                ),
            },
            [
                Result(state=State.CRIT, summary="No NTP server found"),
            ],
            id="crit-if-node-has-no-peers",
        ),
        pytest.param(
            "Node 1",
            None,
            [],
            id="return-nothing-if-ntp-section-is-missing",
        ),
        pytest.param(
            "Node 1",
            {
                "Node 2": NtpStatusModelFactory.build(
                    node="Node 2",
                    peers=[
                        NtpPeerStatusModelFactory.build(
                            server="ntp-1",
                            offset=-1.35,
                            is_peer_selected=True,
                        ),
                    ],
                ),
            },
            [],
            id="return-nothing-if-item-is-not-in-section",
        ),
    ],
)
def test_check_netapp_ontap_time_error_cases(
    item: str,
    ntp_section: Mapping[str, NtpStatusModel] | None,
    expected: Sequence[Result],
) -> None:
    result = list(
        check_netapp_ontap_time(
            item,
            {"offset": ("fixed", (0.001, 0.002))},
            ntp_section,
        )
    )
    assert result == list(expected)
