#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import not_opted_in


def test_only_regions_without_opt_in_are_not_enabled() -> None:
    regions = [
        {"RegionName": "eu-central-1", "OptInStatus": "opt-in-not-required"},
        {"RegionName": "eu-south-2", "OptInStatus": "opted-in"},
        {"RegionName": "me-central-1", "OptInStatus": "not-opted-in"},
    ]

    assert not_opted_in(regions) == {"me-central-1"}
