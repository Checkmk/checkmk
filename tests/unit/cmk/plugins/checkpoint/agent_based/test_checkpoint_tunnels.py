#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.checkpoint.agent_based.checkpoint_tunnels import (
    check_checkpoint_tunnels,
    discover_checkpoint_tunnels,
)

_DEFAULT_PARAMS = {
    "Active": 0,
    "Destroy": 1,
    "Idle": 0,
    "Phase1": 2,
    "Down": 2,
    "Init": 1,
}


def test_discover_checkpoint_tunnels() -> None:
    assert list(discover_checkpoint_tunnels([["peer1", "3"], ["peer2", "131"]])) == [
        Service(item="peer1"),
        Service(item="peer2"),
    ]


def test_check_checkpoint_tunnels_known_status() -> None:
    assert list(check_checkpoint_tunnels("peer1", _DEFAULT_PARAMS, [["peer1", "3"]])) == [
        Result(state=State.OK, summary="Active"),
    ]


@pytest.mark.xfail(
    strict=True,
    reason="Crash report cccb62da-6572-11f1-9919-005056b93709: KeyError on unknown tunnel status",
)
def test_check_checkpoint_tunnels_unknown_status() -> None:
    # Crash group 4803: the device reported a composite, non-numeric status string
    # instead of a single numeric state code, which is not a key in tunnel_states.
    section = [["DELAUTNWFWC01", "Tunnel1 : 3 , Tunnel2 : 3 , Tunnel3 : 3 , Tunnel4 : 3"]]
    assert list(check_checkpoint_tunnels("DELAUTNWFWC01", _DEFAULT_PARAMS, section)) == [
        Result(
            state=State.UNKNOWN,
            summary="Unknown tunnel status: Tunnel1 : 3 , Tunnel2 : 3 , Tunnel3 : 3 , Tunnel4 : 3",
        ),
    ]
