#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The parameters of the "job" check plug-in, shared with its ruleset."""

from collections.abc import Sequence
from typing import TypedDict

from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel


class ExitCodeState(TypedDict):
    """One entry of the explicit mapping of job exit codes to states."""

    exit_code: int
    state: int


class CheckParameters(TypedDict):
    age: SimpleLevelsConfigModel[float]
    exit_code_to_state_map: Sequence[ExitCodeState]
