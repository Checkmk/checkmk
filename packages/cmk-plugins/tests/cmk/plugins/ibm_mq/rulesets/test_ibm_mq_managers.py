#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.ibm_mq.rulesets.ibm_mq_managers import rule_spec_ibm_mq_managers


def _migrate(rule: object) -> object:
    assert (migrate := rule_spec_ibm_mq_managers.parameter_form().migrate) is not None
    return migrate(rule)


def test_listed_manager_states_become_a_mapping() -> None:
    assert _migrate({"mapped_states": [("ended_pre_emptively", 2)]}) == {
        "mapped_states": {"ended_pre_emptively": 2},
    }


def test_default_state_is_set_for_the_manager_states_the_list_left_out() -> None:
    migrated = _migrate({"mapped_states": [("running", 0)], "mapped_states_default": 2})

    assert migrated == {
        "mapped_states": {
            "starting": 2,
            "running": 0,
            "running_as_standby": 2,
            "running_elsewhere": 2,
            "quiescing": 2,
            "ending_immediately": 2,
            "ending_pre_emptively": 2,
            "ended_normally": 2,
            "ended_immediately": 2,
            "ended_unexpectedly": 2,
            "ended_pre_emptively": 2,
            "status_not_available": 2,
        },
        "mapped_states_default": 2,
    }
