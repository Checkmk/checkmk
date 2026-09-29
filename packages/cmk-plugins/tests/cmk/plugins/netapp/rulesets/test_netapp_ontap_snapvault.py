#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.netapp.rulesets.netapp_ontap_snapvault import rule_spec_snapvault
from cmk.rulesets.v1.form_specs import Dictionary


def _migrate(rule_value: Mapping[str, object]) -> dict[str, object]:
    form = rule_spec_snapvault.parameter_form()
    assert isinstance(form, Dictionary)
    migrated = {}
    for key, value in rule_value.items():
        migrate = form.elements[key].parameter_form.migrate
        migrated[key] = value if migrate is None else migrate(value)
    return migrated


MIGRATED_RULE = {
    "lag_time": ("fixed", (3600.0, 7200.0)),
    "policy_lag_time": [{"policy_name": "Asynchronous", "levels": ("fixed", (1800.0, 3600.0))}],
}


@pytest.mark.parametrize(
    "rule_value",
    [
        pytest.param(
            {"lag_time": (3600, 7200), "policy_lag_time": [("Asynchronous", (1800, 3600))]},
            id="legacy rule",
        ),
        pytest.param(MIGRATED_RULE, id="already migrated"),
    ],
)
def test_migrate_rule(rule_value: Mapping[str, object]) -> None:
    assert _migrate(rule_value) == MIGRATED_RULE
