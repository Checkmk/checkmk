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

from typing import Final, Literal

# Livestatus integer state → the string token the SPA renders. Host and service
# use disjoint token sets on purpose (UP/DOWN/UNREACHABLE vs OK/WARNING/...).
HOST_STATE_MAP: Final[dict[int, str]] = {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
SERVICE_STATE_MAP: Final[dict[int, str]] = {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}

# One combined severity scale across host *and* service states, so a worst-state
# roll-up over a mixed set (e.g. a folder or map-link that spans both) orders them
# on a single ladder: PENDING < OK/UP < UNREACHABLE/UNKNOWN < WARNING < DOWN <
# CRITICAL. It also preserves the per-scale order within host-only or
# service-only sets, so ``max(states, key=SEVERITY_RANK.get)`` picks the same
# winner a host-only / service-only scale would.
SEVERITY_RANK: Final[dict[str, int]] = {
    "PENDING": -1,
    "UP": 0,
    "OK": 0,
    "UNREACHABLE": 1,
    "UNKNOWN": 1,
    "WARNING": 2,
    "DOWN": 3,
    "CRITICAL": 4,
}

# The state token of a BI aggregation. BI computes its states GUI-side, as integers.
type BIStateName = Literal["PENDING", "OK", "WARNING", "CRITICAL", "UNKNOWN"]

# The "critical" tier of the problems_severity filter.
CRITICAL_STATES: Final[frozenset[str]] = frozenset({"CRITICAL", "DOWN", "UNREACHABLE"})


def severity_rank(state: str) -> int:
    """Combined worst-state rank (CRITICAL highest); unknown/EMPTY sink to -1."""
    return SEVERITY_RANK.get(state, -1)
