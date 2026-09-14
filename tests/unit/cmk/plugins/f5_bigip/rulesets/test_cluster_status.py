#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.f5_bigip.agent_based.f5_bigip_cluster_status import V11_2_STATE_KEYS
from cmk.plugins.f5_bigip.rulesets.cluster_status import rule_spec_cluster_status
from cmk.rulesets.v1.form_specs import Dictionary


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


def _migrate(rule: Mapping[str, object]) -> object:
    # Migrate the rule the same way it happens during runtime.
    visitor = get_visitor(
        rule_spec_cluster_status.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    return visitor.to_disk(RawDiskData(rule))


_MIGRATED_STATES = {
    "unknown": 3,
    "offline": 2,
    "forced_offline": 2,
    "standby": 0,
    "active": 0,
}


@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param(
            {"type": "active_standby"},
            {"type": "active_standby"},
            id="cluster type only",
        ),
        pytest.param(
            {
                "type": "active_active",
                "v11_2_states": {"0": 3, "1": 2, "2": 2, "3": 0, "4": 0},
            },
            {"type": "active_active", "v11_2_states": _MIGRATED_STATES},
            id="status codes are renamed to the status they stand for",
        ),
        pytest.param(
            {"type": "active_standby", "v11_2_states": {"4": 1}},
            {"type": "active_standby", "v11_2_states": {"active": 1}},
            id="a rule configuring a single status",
        ),
        pytest.param(
            {"type": "active_standby", "v11_2_states": _MIGRATED_STATES},
            {"type": "active_standby", "v11_2_states": _MIGRATED_STATES},
            id="migrated rule stays unchanged",
        ),
    ],
)
@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_rule_spec_cluster_status_migration(
    rule: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(rule) == expected


def test_rule_spec_cluster_status_covers_the_states_the_check_reads() -> None:
    """Every failover status the check looks up has to be configurable."""
    v11_2_states = rule_spec_cluster_status.parameter_form().elements["v11_2_states"]
    assert isinstance(form := v11_2_states.parameter_form, Dictionary)
    assert set(form.elements) == set(V11_2_STATE_KEYS)
