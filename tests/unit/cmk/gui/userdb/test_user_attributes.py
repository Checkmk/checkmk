#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import active_config
from cmk.gui.userdb.user_attributes import (
    GraphDefaultTimeRangeUserAttribute,
    StartOfWeekUserAttribute,
)
from cmk.gui.valuespec import DropdownChoice


@pytest.mark.usefixtures("load_config")
def test_graph_default_time_range_mirrors_configured_timeranges() -> None:
    valuespec = GraphDefaultTimeRangeUserAttribute().valuespec()
    valuespec.validate_value(None, "ua_graph_default_time_range")
    for timerange in active_config.graph_timeranges:
        valuespec.validate_value(timerange["duration"], "ua_graph_default_time_range")


@pytest.mark.usefixtures("load_config")
def test_graph_default_time_range_tolerates_a_removed_duration() -> None:
    # Saving any user validates every registered attribute against the whole stored spec, so a
    # time range an admin removed from the global setting must not block unrelated edits.
    removed_duration = 1234
    assert all(
        timerange["duration"] != removed_duration for timerange in active_config.graph_timeranges
    )
    GraphDefaultTimeRangeUserAttribute().valuespec().validate_value(
        removed_duration, "ua_graph_default_time_range"
    )


def test_start_of_week_offers_monday_first() -> None:
    # Two independent declarations that have to agree: the profile pre-selects choices()[0],
    # while a garbled submit falls back to default_value().
    valuespec = StartOfWeekUserAttribute().valuespec()
    assert isinstance(valuespec, DropdownChoice)
    assert valuespec.choices()[0][0] == "monday"
    assert valuespec.default_value() == "monday"


def test_start_of_week_tolerates_the_legacy_none() -> None:
    StartOfWeekUserAttribute().valuespec().validate_value(None, "ua_start_of_week")
