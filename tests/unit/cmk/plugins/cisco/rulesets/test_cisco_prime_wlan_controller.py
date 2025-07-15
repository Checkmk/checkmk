#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc.version import Edition
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.plugins.cisco.rulesets.prime_wlan_controller import (
    rule_spec_cisco_prime_wlan_controller_access_points,
    rule_spec_cisco_prime_wlan_controller_clients,
    rule_spec_cisco_prime_wlan_controller_last_backup,
)


def test_rule_spec_cisco_prime_wlan_controller_access_points_migration_validation() -> None:
    rule_2_2 = {"access_points": (0, 0)}
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_cisco_prime_wlan_controller_access_points, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule_2_2, "")
    validating_rule_spec.valuespec.validate_value(rule_2_2, "")


def test_rule_spec_cisco_prime_wlan_controller_clients_migration_validation() -> None:
    rule_2_2 = {"clients": (0, 0)}
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_cisco_prime_wlan_controller_clients, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule_2_2, "")
    validating_rule_spec.valuespec.validate_value(rule_2_2, "")


def test_rule_spec_cisco_prime_wlan_controller_last_backup_migration_validation() -> None:
    rule_2_2 = {"last_backup": (604800, 2592000)}
    validating_rule_spec = convert_to_legacy_rulespec(
        rule_spec_cisco_prime_wlan_controller_last_backup, Edition.CRE, lambda x: x
    )
    validating_rule_spec.valuespec.validate_datatype(rule_2_2, "")
    validating_rule_spec.valuespec.validate_value(rule_2_2, "")
