#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.checkpoint_tunnels import (
    check_checkpoint_tunnels,
    inventory_checkpoint_tunnels,
)

_DEFAULT_PARAMS = {
    "Active": 0,
    "Destroy": 1,
    "Idle": 0,
    "Phase1": 2,
    "Down": 2,
    "Init": 1,
}


def test_inventory_checkpoint_tunnels() -> None:
    assert list(inventory_checkpoint_tunnels([["peer1", "3"], ["peer2", "131"]])) == [  # type: ignore[no-untyped-call]
        ("peer1", {}),
        ("peer2", {}),
    ]


def test_check_checkpoint_tunnels_known_status() -> None:
    assert check_checkpoint_tunnels("peer1", _DEFAULT_PARAMS, [["peer1", "3"]]) == (  # type: ignore[no-untyped-call]
        0,
        "Active",
    )


@pytest.mark.xfail(
    strict=True,
    reason="Crash report cccb62da-6572-11f1-9919-005056b93709: KeyError on unknown tunnel status",
)
def test_check_checkpoint_tunnels_unknown_status() -> None:
    # Crash group 4803: the device reported a composite, non-numeric status string
    # instead of a single numeric state code, which is not a key in tunnel_states.
    section = [["DELAUTNWFWC01", "Tunnel1 : 3 , Tunnel2 : 3 , Tunnel3 : 3 , Tunnel4 : 3"]]
    assert check_checkpoint_tunnels("DELAUTNWFWC01", _DEFAULT_PARAMS, section) == (  # type: ignore[no-untyped-call]
        3,
        "Unknown tunnel status: Tunnel1 : 3 , Tunnel2 : 3 , Tunnel3 : 3 , Tunnel4 : 3",
    )
