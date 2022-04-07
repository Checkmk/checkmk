#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypeVar

from ..agent_based_api.v1 import Result, State

_T = TypeVar("_T")


def check_state(missmatch_state: State, label: str, actual: _T, expected: _T) -> Result:
    """
    >>> check_state(State.WARN, "socks", "white", "black")
    Result(state=<State.WARN: 1>, summary='Socks: white (expected: black)')
    """
    short = f"{label.capitalize()}: {actual}"
    if actual == expected:
        return Result(state=State.OK, summary=short)
    return Result(state=missmatch_state, summary=f"{short} (expected: {expected})")
