#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils import aws_constants


def test_display_order_logic() -> None:
    # Assemble
    display_regions = [display_region for _region_id, display_region in aws_constants.AWSRegions]
    # Assert
    # GovCloud entries are generally useful to only very few people. Thus, they should all be
    # displayed at end of the list. Within the groups, the order should be alphabetical.
    assert display_regions == [
        *sorted(region for region in display_regions if "GovCloud" not in region),
        *sorted(region for region in display_regions if "GovCloud" in region),
    ]
