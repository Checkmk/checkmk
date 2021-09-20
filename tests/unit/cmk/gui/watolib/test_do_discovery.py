#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from typing import Any, Dict, List, Set, Tuple

from cmk.gui.watolib.services import _apply_state_change, DiscoveryState

MOCK_KEY: Tuple[str, str] = ("local", "1st service")
MOCK_VALUE: Tuple[str, Dict[str, Any], Dict[str, Any], List[str]] = (
    "1st service",
    {},
    {},
    ["test"],
)
MOCK_DESC = "1st service"

RESULT = Tuple[Dict, Set, Set, Set]


def _expected_clustered():
    return (
        {MOCK_KEY: MOCK_VALUE},
        {MOCK_DESC},
        set(),
        set(),
    )


# TODO Find a better name
def _expected_monitored_standard():
    return (
        {},
        {MOCK_DESC},
        set(),
        set(),
    )


# TODO Find a better name
def _expected_vanished_standard():
    return (
        {MOCK_KEY: MOCK_VALUE},
        {MOCK_DESC},
        set(),
        set(),
    )


# TODO Find a better name
def _expected_ignored_standard():
    return (
        {},
        set(),
        set(),
        set(),
    )


def _get_combinations() -> List:
    states = [value for state, value in vars(DiscoveryState).items() if state.isupper()]
    return list(itertools.combinations_with_replacement(states, 2))


known_results = {
    (DiscoveryState.MONITORED, DiscoveryState.MONITORED): (
        {MOCK_KEY: MOCK_VALUE},
        {MOCK_DESC},
        set(),
        set(),
    ),
    (DiscoveryState.MONITORED, DiscoveryState.UNDECIDED): (
        {},
        {MOCK_DESC},
        set(),
        set(),
    ),
    (DiscoveryState.MONITORED, DiscoveryState.IGNORED): (
        {MOCK_KEY: MOCK_VALUE},
        set(),
        {MOCK_DESC},
        set(),
    ),
    (DiscoveryState.MONITORED, DiscoveryState.VANISHED): _expected_monitored_standard(),
    (DiscoveryState.MONITORED, DiscoveryState.REMOVED): _expected_monitored_standard(),
    (DiscoveryState.MONITORED, DiscoveryState.MANUAL): _expected_monitored_standard(),
    (DiscoveryState.MONITORED, DiscoveryState.ACTIVE): _expected_monitored_standard(),
    (DiscoveryState.MONITORED, DiscoveryState.CUSTOM): _expected_monitored_standard(),
    (
        DiscoveryState.MONITORED,
        DiscoveryState.CLUSTERED_OLD,
    ): _expected_monitored_standard(),
    (
        DiscoveryState.MONITORED,
        DiscoveryState.CLUSTERED_NEW,
    ): _expected_monitored_standard(),
    (
        DiscoveryState.MONITORED,
        DiscoveryState.CLUSTERED_VANISHED,
    ): _expected_monitored_standard(),
    (
        DiscoveryState.MONITORED,
        DiscoveryState.CLUSTERED_IGNORED,
    ): _expected_monitored_standard(),
    (
        DiscoveryState.MONITORED,
        DiscoveryState.ACTIVE_IGNORED,
    ): _expected_monitored_standard(),
    (
        DiscoveryState.MONITORED,
        DiscoveryState.CUSTOM_IGNORED,
    ): _expected_monitored_standard(),
    (DiscoveryState.MONITORED, DiscoveryState.LEGACY): _expected_monitored_standard(),
    (
        DiscoveryState.MONITORED,
        DiscoveryState.LEGACY_IGNORED,
    ): _expected_monitored_standard(),
    (DiscoveryState.VANISHED, DiscoveryState.IGNORED): (
        {MOCK_KEY: MOCK_VALUE},
        set(),
        {MOCK_DESC},
        set(),
    ),
    (DiscoveryState.VANISHED, DiscoveryState.VANISHED): _expected_vanished_standard(),
    (DiscoveryState.VANISHED, DiscoveryState.MONITORED): _expected_vanished_standard(),
    (DiscoveryState.VANISHED, DiscoveryState.MANUAL): _expected_vanished_standard(),
    (DiscoveryState.VANISHED, DiscoveryState.ACTIVE): _expected_vanished_standard(),
    (DiscoveryState.VANISHED, DiscoveryState.CUSTOM): _expected_vanished_standard(),
    (
        DiscoveryState.VANISHED,
        DiscoveryState.CLUSTERED_OLD,
    ): _expected_vanished_standard(),
    (
        DiscoveryState.VANISHED,
        DiscoveryState.CLUSTERED_NEW,
    ): _expected_vanished_standard(),
    (
        DiscoveryState.VANISHED,
        DiscoveryState.CLUSTERED_VANISHED,
    ): _expected_vanished_standard(),
    (
        DiscoveryState.VANISHED,
        DiscoveryState.CLUSTERED_IGNORED,
    ): _expected_vanished_standard(),
    (
        DiscoveryState.VANISHED,
        DiscoveryState.ACTIVE_IGNORED,
    ): _expected_vanished_standard(),
    (
        DiscoveryState.VANISHED,
        DiscoveryState.CUSTOM_IGNORED,
    ): _expected_vanished_standard(),
    (DiscoveryState.VANISHED, DiscoveryState.LEGACY): _expected_vanished_standard(),
    (
        DiscoveryState.VANISHED,
        DiscoveryState.LEGACY_IGNORED,
    ): _expected_vanished_standard(),
    (DiscoveryState.UNDECIDED, DiscoveryState.MONITORED): (
        {MOCK_KEY: MOCK_VALUE},
        {MOCK_DESC},
        set(),
        set(),
    ),
    (DiscoveryState.UNDECIDED, DiscoveryState.IGNORED): (
        {},
        set(),
        {MOCK_DESC},
        set(),
    ),
    (DiscoveryState.IGNORED, DiscoveryState.MONITORED): (
        {MOCK_KEY: MOCK_VALUE},
        {MOCK_DESC},
        set(),
        {MOCK_DESC},
    ),
    (DiscoveryState.IGNORED, DiscoveryState.IGNORED): (
        {MOCK_KEY: MOCK_VALUE},
        {MOCK_DESC},
        {MOCK_DESC},
        set(),
    ),
    (DiscoveryState.IGNORED, DiscoveryState.UNDECIDED): (
        {},
        set(),
        set(),
        {MOCK_DESC},
    ),
    (DiscoveryState.IGNORED, DiscoveryState.VANISHED): (
        {},
        set(),
        set(),
        {MOCK_DESC},
    ),
    (DiscoveryState.IGNORED, DiscoveryState.REMOVED): _expected_ignored_standard(),
    (DiscoveryState.IGNORED, DiscoveryState.MANUAL): _expected_ignored_standard(),
    (DiscoveryState.IGNORED, DiscoveryState.ACTIVE): _expected_ignored_standard(),
    (DiscoveryState.IGNORED, DiscoveryState.CUSTOM): _expected_ignored_standard(),
    (
        DiscoveryState.IGNORED,
        DiscoveryState.CLUSTERED_OLD,
    ): _expected_ignored_standard(),
    (
        DiscoveryState.IGNORED,
        DiscoveryState.CLUSTERED_NEW,
    ): _expected_ignored_standard(),
    (
        DiscoveryState.IGNORED,
        DiscoveryState.CLUSTERED_VANISHED,
    ): _expected_ignored_standard(),
    (
        DiscoveryState.IGNORED,
        DiscoveryState.CLUSTERED_IGNORED,
    ): _expected_ignored_standard(),
    (
        DiscoveryState.IGNORED,
        DiscoveryState.ACTIVE_IGNORED,
    ): _expected_ignored_standard(),
    (
        DiscoveryState.IGNORED,
        DiscoveryState.CUSTOM_IGNORED,
    ): _expected_ignored_standard(),
    (DiscoveryState.IGNORED, DiscoveryState.LEGACY): _expected_ignored_standard(),
    (
        DiscoveryState.IGNORED,
        DiscoveryState.LEGACY_IGNORED,
    ): _expected_ignored_standard(),
    (DiscoveryState.CLUSTERED_OLD, DiscoveryState.CLUSTERED_NEW): _expected_clustered(),
    (DiscoveryState.CLUSTERED_OLD, DiscoveryState.CLUSTERED_OLD): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_OLD,
        DiscoveryState.ACTIVE_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_OLD,
        DiscoveryState.CUSTOM_IGNORED,
    ): _expected_clustered(),
    (DiscoveryState.CLUSTERED_OLD, DiscoveryState.LEGACY): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_OLD,
        DiscoveryState.LEGACY_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_OLD,
        DiscoveryState.CLUSTERED_VANISHED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_OLD,
        DiscoveryState.CLUSTERED_IGNORED,
    ): _expected_clustered(),
    (DiscoveryState.CLUSTERED_NEW, DiscoveryState.CLUSTERED_OLD): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_NEW,
        DiscoveryState.CLUSTERED_VANISHED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_NEW,
        DiscoveryState.CLUSTERED_NEW,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_NEW,
        DiscoveryState.ACTIVE_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_NEW,
        DiscoveryState.CUSTOM_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_NEW,
        DiscoveryState.LEGACY,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_NEW,
        DiscoveryState.LEGACY_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_NEW,
        DiscoveryState.CLUSTERED_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_IGNORED,
        DiscoveryState.CLUSTERED_VANISHED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_IGNORED,
        DiscoveryState.CLUSTERED_NEW,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_IGNORED,
        DiscoveryState.CLUSTERED_OLD,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_IGNORED,
        DiscoveryState.CLUSTERED_OLD,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_IGNORED,
        DiscoveryState.CLUSTERED_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_IGNORED,
        DiscoveryState.ACTIVE_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_IGNORED,
        DiscoveryState.CUSTOM_IGNORED,
    ): _expected_clustered(),
    (DiscoveryState.CLUSTERED_IGNORED, DiscoveryState.LEGACY): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_IGNORED,
        DiscoveryState.LEGACY_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_VANISHED,
        DiscoveryState.CLUSTERED_VANISHED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_VANISHED,
        DiscoveryState.CLUSTERED_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_VANISHED,
        DiscoveryState.CLUSTERED_OLD,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_VANISHED,
        DiscoveryState.ACTIVE_IGNORED,
    ): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_VANISHED,
        DiscoveryState.CUSTOM_IGNORED,
    ): _expected_clustered(),
    (DiscoveryState.CLUSTERED_VANISHED, DiscoveryState.LEGACY): _expected_clustered(),
    (
        DiscoveryState.CLUSTERED_VANISHED,
        DiscoveryState.LEGACY_IGNORED,
    ): _expected_clustered(),
}

empty_result: RESULT = (
    {},
    set(),
    set(),
    set(),
)


def test_apply_state_change():

    for table_source, table_target in _get_combinations():
        result: RESULT = {}, set(), set(), set()
        _apply_state_change(
            table_source,
            table_target,
            MOCK_KEY,
            MOCK_VALUE,
            MOCK_DESC,
            *result,
        )
        error_msg = "Error while applying changes from %s to %s" % (table_source, table_target)
        assert known_results.get((table_source, table_target), empty_result) == result, error_msg
