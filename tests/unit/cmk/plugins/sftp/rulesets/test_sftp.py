#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.sftp.rulesets.active_check import rule_spec_active_check_sftp


def test_rule_spec_active_check_sftp__migrated_2_3__values_pass_validation() -> None:
    rule_2_3 = (
        "my_test_host",
        "my_test_name",
        ("password", "my_test_pwd"),
        {
            "description": "My SFTP",
            "port": 25,
            "look_for_keys": True,
            "timeout": 20,
            "timestamp": "1234",
            "put": ("my_testfile", "remote_testfile"),
            "get": ("other_remote_file", "other_local_file"),
        },
    )
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_active_check_sftp, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule_2_3, "")
    validating_rule_spec.valuespec.validate_value(rule_2_3, "")
