#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.aws.rulesets.aws_status import rule_spec_aws_status


def test_aws_status_vs_to_fs_rule_update_valid_datatypes() -> None:
    # GIVEN
    valuespec = convert_to_legacy_rulespec(rule_spec_aws_status, Edition.CRE, lambda x: x).valuespec

    # WHEN
    value = valuespec.transform_value({"regions": ["ap-northeast-2", "ca-central-1"]})
    valuespec.validate_datatype(value, "")

    # THEN
    assert value["regions_to_monitor"] == ["ap_northeast_2", "ca_central_1"]
