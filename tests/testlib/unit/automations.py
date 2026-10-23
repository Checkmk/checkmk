#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helpers for testing automation handlers."""

import dataclasses

import cmk.utils.paths
from cmk.base.automations.states import CommonState
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.config import LoadingResult

from .empty_config import EMPTY_CONFIG


def make_common_state(
    loading_result: LoadingResult, *, app: CheckmkBaseApp | None = None
) -> CommonState:
    """A state that hands the handler the given loading result, and app if given.

    A CommonState derives everything from a raw configuration. The tests usually
    prepare the derived objects themselves, so we derive from the empty
    configuration and put in what the test prepared.
    """
    state = CommonState(
        cmk.utils.paths.omd_root,
        {f.name: getattr(EMPTY_CONFIG, f.name) for f in dataclasses.fields(EMPTY_CONFIG)},
    )
    state.loading_result = loading_result
    if app is not None:
        state.app = app
    return state
