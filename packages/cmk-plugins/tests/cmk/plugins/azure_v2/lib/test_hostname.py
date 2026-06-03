#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.plugins.azure_v2.lib import compute_unique_name_hash


@pytest.mark.parametrize(
    "uniqueness_keys, expected_hash",
    [
        # Pinned values: must stay identical to the hashes the special agent
        # produced before the extraction (see piggytarget tests in
        # special_agent/test_agent_azure_subscriptions.py).
        pytest.param(
            ("subscription_id_12345678",),
            "2a0cae26",
            id="subscription",
        ),
        pytest.param(
            ("subscription_id", "Microsoft.Resources/resourceGroups"),
            "5d6f43b3",
            id="resource_group",
        ),
        pytest.param(
            ("subscription_id_12345678", "group1", "Microsoft.Compute/virtualMachines"),
            "6429882c",
            id="resource",
        ),
    ],
)
def test_compute_unique_name_hash(uniqueness_keys: Sequence[str], expected_hash: str) -> None:
    assert compute_unique_name_hash(uniqueness_keys) == expected_hash, (
        f"Hash for {uniqueness_keys} should be {expected_hash}"
    )
