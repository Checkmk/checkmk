#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"


from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Result, Service, State
from cmk.plugins.synology.agent_based import synology_update

SECTION_TABLE = [
    ["nana batman", "0"],
]

DEFAULT_PARAMS: Mapping[str, Sequence[int]] = {
    "ok_states": [2],
    "warn_states": [5],
    "crit_states": [1, 4],
}


def test_parsing() -> None:
    section = synology_update.parse(SECTION_TABLE)
    assert section == synology_update.Section(version="nana batman", status=0)


def test_discovery() -> None:
    section = synology_update.parse(SECTION_TABLE)
    assert section is not None
    service = list(synology_update.discovery(section))[0]
    assert service == Service()


@pytest.mark.parametrize("cmk_state", [State.OK, State.WARN, State.CRIT])
@pytest.mark.parametrize("observed_state", range(1, 6))
def test_result_state(cmk_state: State, observed_state: int) -> None:
    state_names = {State.OK: "ok_states", State.WARN: "warn_states", State.CRIT: "crit_states"}
    params: dict[str, object] = {name: [] for name in ["ok_states", "warn_states", "crit_states"]}
    params[state_names[cmk_state]] = [1, 2, 3, 4, 5]
    section = synology_update.Section(version="robin", status=observed_state)
    assert section is not None
    result = list(synology_update.check(section=section, params=params))[0]
    assert isinstance(result, Result)
    assert result.state == cmk_state


@pytest.mark.parametrize(
    "status, expected_result",
    [
        pytest.param(
            2,
            Result(state=State.OK, summary="Update Status: Unavailable, Current Version: robin"),
            id="unavailable_is_ok_by_default",
        ),
        pytest.param(
            5,
            Result(state=State.WARN, summary="Update Status: Others, Current Version: robin"),
            id="others_warns_by_default",
        ),
        pytest.param(
            1,
            Result(state=State.CRIT, summary="Update Status: Available, Current Version: robin"),
            id="an_available_update_is_crit_by_default",
        ),
        pytest.param(
            4,
            Result(state=State.CRIT, summary="Update Status: Disconnected, Current Version: robin"),
            id="disconnected_is_crit_by_default",
        ),
    ],
)
def test_check_with_the_default_parameters(status: int, expected_result: Result) -> None:
    section = synology_update.Section(version="robin", status=status)

    assert list(synology_update.check(section=section, params=DEFAULT_PARAMS)) == [expected_result]


def test_raise_if_connection_not_explicit_named_in_states() -> None:
    section = synology_update.Section(version="robin", status=3)
    with pytest.raises(IgnoreResultsError):
        list(synology_update.check(section=section, params=DEFAULT_PARAMS))


def test_connecting_is_reported_when_a_rule_names_it() -> None:
    """The status-3 IgnoreResults is the last branch, so a rule that lists it still wins."""
    params: Mapping[str, Sequence[int]] = {"ok_states": [3], "warn_states": [], "crit_states": []}
    section = synology_update.Section(version="robin", status=3)

    assert list(synology_update.check(section=section, params=params)) == [
        Result(state=State.OK, summary="Update Status: Connecting, Current Version: robin")
    ]
