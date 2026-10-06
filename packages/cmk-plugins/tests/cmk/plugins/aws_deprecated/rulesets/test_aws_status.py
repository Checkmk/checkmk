#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.plugins.aws_deprecated.rulesets.aws_status import pre_24_to_formspec_migration


def test_aws_status_vs_to_fs_rule_update_valid_datatypes() -> None:
    assert pre_24_to_formspec_migration({"regions": ["ap-northeast-2", "ca-central-1"]}) == {
        "regions_to_monitor": ["ap_northeast_2", "ca_central_1"]
    }
