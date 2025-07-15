#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import pprint
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from typing import Final, TypedDict

import cmk.ccc.debug
from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.parameters import merge_parameters
from cmk.utils.timeperiod import TimeperiodName

__all__ = [
    "Parameters",
    "TimespecificParameters",
    "TimespecificParametersPreview",
    "TimespecificParameterSet",
]


class Parameters(ParametersTypeAlias):
    """Parameter objects are used to pass parameters to plug-in functions"""

    def __init__(self, data: ParametersTypeAlias) -> None:
        self._data = dict(data)

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __repr__(self) -> str:
        # use pformat to be testable.
        return f"{self.__class__.__name__}({pprint.pformat(self._data)})"


_IsTimeperiodActiveCallback = Callable[[TimeperiodName], bool | None]


class _InnerTimespecificParametersPreview(TypedDict):
    params: Mapping[str, object]
    computed_at: float


class TimespecificParametersPreview(TypedDict):
    tp_computed_params: _InnerTimespecificParametersPreview


class TimespecificParameters:
    def __init__(self, entries: Sequence[TimespecificParameterSet] = ()) -> None:
        self.entries: Final = tuple(entries)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TimespecificParameters) and self.entries == other.entries

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.entries!r})"

    def evaluate(self, is_active: _IsTimeperiodActiveCallback) -> Mapping[str, object]:
        return merge_parameters(
            [entry.evaluate(is_active) for entry in self.entries],
            {},
        )

    def is_constant(self) -> bool:
        return not any(p.timeperiod_values for p in self.entries)

    def preview(
        self, is_active: _IsTimeperiodActiveCallback
    ) -> TimespecificParametersPreview | Mapping[str, object]:
        """Create a serializeable version for preview via automation call"""
        if self.is_constant():
            return self.evaluate(is_active)
        return {
            "tp_computed_params": {
                "params": self.evaluate(is_active),
                "computed_at": time.time(),
            }
        }


# see how much logic of the time period evaluation has to end up here,
# then decide whether to move this to type defs.
class TimespecificParameterSet:
    def __init__(
        self,
        default: Mapping[str, object],
        timeperiod_values: Sequence[tuple[TimeperiodName, Mapping[str, object]]],
    ) -> None:
        self.default: Final = default
        self.timeperiod_values: Final = tuple(timeperiod_values)

    @classmethod
    def from_parameters(cls, parameters: Mapping[str, object]) -> TimespecificParameterSet:
        if (
            "tp_default_value" in parameters
            and isinstance((default := parameters["tp_default_value"]), dict)
            and isinstance((tp_values := parameters["tp_values"]), list)
        ):
            return cls(default, tp_values)
        return cls(parameters, ())

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, TimespecificParameterSet)
            and self.default == other.default
            and self.timeperiod_values == other.timeperiod_values
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.default!r}, {self.timeperiod_values!r})"

    def _active_subsets(
        self,
        is_active: _IsTimeperiodActiveCallback,
    ) -> Iterable[Mapping[str, object]]:
        for timeperiod_name, tp_entry in self.timeperiod_values:
            try:
                if is_active(timeperiod_name):
                    yield tp_entry
            except Exception:
                # Connection error
                if cmk.ccc.debug.enabled():
                    raise
                return

    def evaluate(self, is_active: _IsTimeperiodActiveCallback) -> Mapping[str, object]:
        return merge_parameters(list(self._active_subsets(is_active)), self.default)
