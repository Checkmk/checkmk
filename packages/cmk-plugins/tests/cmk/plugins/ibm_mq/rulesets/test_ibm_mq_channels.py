#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.ibm_mq.rulesets.ibm_mq_channels import rule_spec_ibm_mq_channels


def _migrate(rule: object) -> object:
    assert (migrate := rule_spec_ibm_mq_channels.parameter_form().migrate) is not None
    return migrate(rule)


def test_listed_channel_states_become_a_mapping() -> None:
    assert _migrate({"mapped_states": [("stopped", 1), ("retrying", 2)]}) == {
        "mapped_states": {"stopped": 1, "retrying": 2},
    }


def test_default_state_is_set_for_the_channel_states_the_list_left_out() -> None:
    assert _migrate({"mapped_states": [("retrying", 1)], "mapped_states_default": 3}) == {
        "mapped_states": {
            "inactive": 3,
            "initializing": 3,
            "binding": 3,
            "starting": 3,
            "running": 3,
            "retrying": 1,
            "stopping": 3,
            "stopped": 3,
        },
        "mapped_states_default": 3,
    }


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param({}, id="empty rule"),
        pytest.param({"mapped_states_default": 1}, id="default state only"),
        pytest.param(
            {"mapped_states": {"stopped": 1}, "mapped_states_default": 2}, id="migrated rule"
        ),
    ],
)
def test_rule_without_listed_channel_states_stays_unchanged(rule: dict[str, object]) -> None:
    assert _migrate(rule) == rule
