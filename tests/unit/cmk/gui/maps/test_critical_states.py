#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import get_args

from cmk.maps.shared.states import CRITICAL_STATES
from cmk.shared_typing.maps_states import MapsCriticalState


def test_daemon_and_app_count_the_same_states_as_critical() -> None:
    # The app's problems-only filter is typed against MapsCriticalState, the
    # daemon prunes the folder tree by CRITICAL_STATES.
    assert frozenset(get_args(MapsCriticalState.__value__)) == CRITICAL_STATES
