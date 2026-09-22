#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Service
from cmk.plugins.collection.agent_based.brocade_mlx_fan import discover_brocade_mlx_fan


def test_discover_brocade_mlx_fan_skips_rows_without_a_name() -> None:
    # A row with an empty fan index leaves nothing to name the service with:
    # the description is dropped as well when it is empty or carries an RPM
    # reading. Observed on an MLX switch, where it aborted the discovery of the
    # whole host.
    assert list(
        discover_brocade_mlx_fan(
            [
                ["1", "Fan 1", "2"],
                ["", "", "2"],
                ["", "Fan 3 (RPM 2900)", "2"],
            ]
        )
    ) == [Service(item="1 Fan 1")]
