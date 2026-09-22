#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.collection.agent_based.brocade_mlx_fan import inventory_brocade_mlx_fan


@pytest.mark.xfail(
    strict=True,
    reason="Crash report 71b88a82-a86e-11f1-bde5-005056ba4f05: TypeError: 'item' must be a non empty string",
)
def test_inventory_brocade_mlx_fan_skips_rows_without_a_name() -> None:
    # A row with an empty fan index leaves nothing to name the service with:
    # the description is dropped as well when it is empty or carries an RPM
    # reading. Observed on an MLX switch, where it aborted the discovery of the
    # whole host.
    assert list(
        inventory_brocade_mlx_fan(
            [
                ["1", "Fan 1", "2"],
                ["", "", "2"],
                ["", "Fan 3 (RPM 2900)", "2"],
            ]
        )
    ) == [Service(item="1 Fan 1")]
