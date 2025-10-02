#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.lib.elphase import ElPhase, ReadingWithState
from cmk.plugins.ups_modulys.agent_based.ups_modulys_inphase import parse_ups_modulys_inphase


def test_parse_ups_modulys_inphase() -> None:
    assert parse_ups_modulys_inphase(
        [["3", "500", "2314", "134", "500", "2316", "135", "500", "2307", "136"]]
    ) == {
        "Phase 1": ElPhase(
            current=ReadingWithState(value=13.4),
            frequency=ReadingWithState(value=50.0),
            voltage=ReadingWithState(value=231.4),
        ),
        "Phase 2": ElPhase(
            current=ReadingWithState(value=13.5),
            frequency=ReadingWithState(value=50.0),
            voltage=ReadingWithState(value=231.6),
        ),
        "Phase 3": ElPhase(
            current=ReadingWithState(value=13.6),
            frequency=ReadingWithState(value=50.0),
            voltage=ReadingWithState(value=230.7),
        ),
    }


def test_parse_ups_modulys_inphase_with_nulls() -> None:
    assert parse_ups_modulys_inphase(
        [["3", "500", "2360", "NULL", "500", "2360", "NULL", "500", "2378", "NULL"]]
    ) == {
        "Phase 1": ElPhase(
            frequency=ReadingWithState(value=50.0),
            voltage=ReadingWithState(value=236.0),
        ),
        "Phase 2": ElPhase(
            frequency=ReadingWithState(value=50.0),
            voltage=ReadingWithState(value=236.0),
        ),
        "Phase 3": ElPhase(
            frequency=ReadingWithState(value=50.0),
            voltage=ReadingWithState(value=237.8),
        ),
    }
