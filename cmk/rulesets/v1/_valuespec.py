#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from cmk.rulesets.v1._localize import Localizable


@dataclass
class TextInput:
    title: Localizable


@dataclass
class DropdownChoice:
    ...


@dataclass(frozen=True)
class DictElement:
    spec: "ValueSpec"


@dataclass
class Dictionary:
    elements: Mapping[str, DictElement]  # TODO check if key is a valid Python identifier


class State(enum.Enum):
    # Don't use IntEnum to prevent "state.CRIT < state.UNKNOWN" from evaluating to True.
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3


@dataclass(frozen=True)
class MonitoringState:
    title: Localizable
    default_value: State = State.OK
    elements: Sequence[tuple[State, str]] = field(
        default_factory=lambda: [(state, state.name) for state in State]
    )


ItemSpec = TextInput | DropdownChoice

ValueSpec = TextInput | DropdownChoice | Dictionary | MonitoringState
