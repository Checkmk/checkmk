#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Result, Service, State
from cmk.plugins.collection.agent_based import synology_update

SECTION_TABLE = [
    ["nana batman", "0"],
]


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
    params: dict[str, Any] = {name: [] for name in ["ok_states", "warn_states", "crit_states"]}
    params[state_names[cmk_state]] = [1, 2, 3, 4, 5]
    section = synology_update.Section(version="robin", status=observed_state)
    assert section is not None
    result = list(synology_update.check(section=section, params=params))[0]
    assert isinstance(result, Result)
    assert result.state == cmk_state


def test_raise_if_connection_not_explicit_named_in_states() -> None:
    params = {
        "ok_states": [2],
        "warn_states": [5],
        "crit_states": [1, 4],
    }
    section = synology_update.Section(version="robin", status=3)
    with pytest.raises(IgnoreResultsError):
        list(synology_update.check(section=section, params=params))
