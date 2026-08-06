#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.synology.agent_based.synology_update import Status
from cmk.plugins.synology.rulesets.synology_update import _migrate, _UPDATE_STATES


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            {"ok_states": [2], "warn_states": [5], "crit_states": [1, 4]},
            {
                "ok_states": ["unavailable"],
                "warn_states": ["others"],
                "crit_states": ["available", "disconnected"],
            },
            id="the_shipped_defaults",
        ),
        pytest.param(
            {"ok_states": ["unavailable"], "warn_states": [], "crit_states": []},
            {"ok_states": ["unavailable"], "warn_states": [], "crit_states": []},
            id="already_migrated",
        ),
        pytest.param(
            {"ok_states": [], "warn_states": [], "crit_states": []},
            {"ok_states": [], "warn_states": [], "crit_states": []},
            id="empty_lists",
        ),
        pytest.param(
            {"ok_states": [9], "warn_states": [], "crit_states": []},
            {"ok_states": ["9"], "warn_states": [], "crit_states": []},
            id="a_status_the_mib_does_not_define_is_kept_as_text",
        ),
    ],
)
def test_migrate_maps_mib_values_onto_element_names(
    old: dict[str, object], expected: dict[str, object]
) -> None:
    """The legacy ListChoice stored raw SYNOLOGY-SYSTEM-MIB integers, but a
    MultipleChoiceElement name has to be a Python identifier."""
    assert _migrate(old) == expected


def test_migrate_rejects_a_value_that_is_not_a_dictionary() -> None:
    with pytest.raises(TypeError):
        _migrate([2])


def test_every_status_but_connecting_is_offered_as_a_choice() -> None:
    assert {element.name for element in _UPDATE_STATES} == {
        status.ruleset_name for status in Status if status is not Status.CONNECTING
    }
