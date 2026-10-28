#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI↔daemon monitoring-state vocabulary for Checkmk Maps.

The Maps daemon (``cmk.maps.backend``) and the GUI (``cmk.maps.gui``) both turn
Livestatus integer states into the string tokens the SPA renders, and both rank
those tokens by severity for worst-state roll-ups. Neither component may import
the other (module-layer boundary), so this shared vocabulary lives in
``cmk.maps.shared`` — the same seam as ``cmk.maps.shared.ticket`` /
``cmk.maps.shared.config_vars``. Keeping the tokens here means the wire vocabulary
(which the frontend also renders) can't drift by a stray edit on one side.

The critical states are also defined in ``cmk-shared-typing``, which generates the
frontend's type for them; ``tests/unit/cmk/gui/maps/test_critical_states.py`` pins
this set to that definition, since this layer may not import it.
"""

from collections.abc import Mapping
from typing import Final, Literal

# Livestatus integer state → the string token the SPA renders. Host and service
# use disjoint token sets on purpose (UP/DOWN/UNREACHABLE vs OK/WARNING/...).
HOST_STATE_MAP: Final[dict[int, str]] = {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
SERVICE_STATE_MAP: Final[dict[int, str]] = {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}


def state_token(state: int, has_been_checked: bool, states: Mapping[int, str]) -> str:
    """The token of a Livestatus host or service state.

    The core reports an object that was never checked as state 0, which would
    read as UP / OK; the views show it as pending.
    """
    if not has_been_checked:
        return "PENDING"
    return states.get(state, "UNKNOWN")


# One combined severity scale across host *and* service states, so a worst-state
# roll-up over a mixed set (e.g. a folder or map-link that spans both) orders them
# on a single ladder. Host problems outrank service problems, as in NagVis: a host
# that is gone is what the map has to show, its services' states are a
# consequence. Within each scale the order stays, so a host-only or service-only
# set picks the same winner as on its own scale. UNKNOWN ranks above WARNING, as
# in Checkmk's views, BI and ``worst_service_state``.
SEVERITY_RANK: Final[dict[str, int]] = {
    "PENDING": -1,
    "UP": 0,
    "OK": 0,
    "WARNING": 1,
    "UNKNOWN": 2,
    "CRITICAL": 3,
    "UNREACHABLE": 4,
    "DOWN": 5,
}

# The state token of a BI aggregation. BI computes its states GUI-side, as integers.
type BIStateName = Literal["PENDING", "OK", "WARNING", "CRITICAL", "UNKNOWN"]

# The "critical" tier of the problems_severity filter.
CRITICAL_STATES: Final[frozenset[str]] = frozenset({"CRITICAL", "DOWN", "UNREACHABLE"})


def severity_rank(state: str) -> int:
    """Combined worst-state rank (DOWN highest); unknown/EMPTY sink to -1."""
    return SEVERITY_RANK.get(state, -1)
