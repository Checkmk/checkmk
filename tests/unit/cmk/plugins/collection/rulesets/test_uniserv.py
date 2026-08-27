#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

from cmk.plugins.collection.rulesets.uniserv import rule_spec_active_check_uniserv
from cmk.plugins.collection.server_side_calls.check_uniserv import active_check_uniserv
from cmk.server_side_calls.v1 import HostConfig, IPv4Config

_ADDRESS = {
    "street": "SomeStreet",
    "street_no": 1,
    "city": "SomeCity",
    "search_regex": "SomeCity",
}


@pytest.mark.parametrize(
    ["rule", "expected_value", "expected_services"],
    [
        pytest.param(
            {"port": 18004, "service": "post_d", "job": "version"},
            {
                "port": 18004,
                "service": "post_d",
                "check_version": True,
                "check_address": ("no", None),
            },
            ["Uniserv post_d Version"],
            id="2.3 rule querying the version",
        ),
        pytest.param(
            {"port": 18004, "service": "post_d", "job": ("address", _ADDRESS)},
            {
                "port": 18004,
                "service": "post_d",
                "check_version": False,
                "check_address": ("yes", _ADDRESS),
            },
            ["Uniserv post_d Address SomeCity"],
            id="2.3 rule querying an address",
        ),
        pytest.param(
            {"port": 18004, "service": "post_d", "check_version": True},
            {
                "port": 18004,
                "service": "post_d",
                "check_version": True,
                "check_address": ("no", None),
            },
            ["Uniserv post_d Version"],
            id="rule left incomplete by an earlier 2.4 migration",
        ),
        pytest.param(
            {
                "port": 18004,
                "service": "post_d",
                "check_version": True,
                "check_address": ("no", None),
            },
            {
                "port": 18004,
                "service": "post_d",
                "check_version": True,
                "check_address": ("no", None),
            },
            ["Uniserv post_d Version"],
            id="valid 2.4 rule querying the version",
        ),
        pytest.param(
            {
                "port": 18004,
                "service": "post_d",
                "check_version": False,
                "check_address": ("yes", _ADDRESS),
            },
            {
                "port": 18004,
                "service": "post_d",
                "check_version": False,
                "check_address": ("yes", _ADDRESS),
            },
            ["Uniserv post_d Address SomeCity"],
            id="valid 2.4 rule querying an address",
        ),
    ],
)
def test_rule_spec_uniserv_migration(
    rule: dict[str, object],
    expected_value: Mapping[str, object],
    expected_services: Sequence[str],
) -> None:
    """Mirror the update: migrate the rule, validate it, then let the plug-in parse it"""
    legacy_rule_spec = convert_to_legacy_rulespec(
        rule_spec_active_check_uniserv, Edition.CRE, lambda x: x
    )

    migrated = legacy_rule_spec.valuespec.transform_value(rule)
    assert migrated == expected_value

    legacy_rule_spec.valuespec.validate_datatype(migrated, "")
    legacy_rule_spec.valuespec.validate_value(migrated, "")

    commands = active_check_uniserv(
        migrated, HostConfig(name="host", ipv4_config=IPv4Config(address="1.2.3.4"))
    )
    assert [command.service_description for command in commands] == list(expected_services)
