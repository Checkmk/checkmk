#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import time
from typing import Any, Callable, Final, Iterable, Optional, Sequence, Tuple, TypedDict, Union

import cmk.utils.debug
from cmk.utils.type_defs import LegacyCheckParameters, TimeperiodName

_IsTimeperiodActiveCallback = Callable[[TimeperiodName], Optional[bool]]


class _InnerTimespecificParametersPreview(TypedDict):
    params: LegacyCheckParameters
    computed_at: float


class TimespecificParametersPreview(TypedDict):
    tp_computed_params: _InnerTimespecificParametersPreview


# this is not particularly clever, but an easy way to allow for
# an instance check (for the transitioning phase)
class TimespecificParameters:
    def __init__(self, entries: Sequence[TimespecificParameterSet] = ()) -> None:
        self.entries: Final = tuple(entries)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TimespecificParameters) and self.entries == other.entries

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.entries!r})"

    def evaluate(self, is_active: _IsTimeperiodActiveCallback) -> LegacyCheckParameters:
        # This is kept for compatibility. I am not sure if we shouldn't make this more consistent
        if self.entries and not isinstance(self.entries[0].default, dict):
            return self.entries[0].evaluate(is_active)

        return boil_down_parameters(
            # Ignore parameters derived from old parameters like
            #   'NAME_default_levels' = (80.0, 85.0)
            (
                entry.evaluate(is_active)
                for entry in self.entries
                if isinstance(entry.default, dict) or entry.timeperiod_values
            ),
            {},
        )

    def _is_constant(self) -> bool:
        return not any(p.timeperiod_values for p in self.entries)

    def preview(
        self, is_active: _IsTimeperiodActiveCallback
    ) -> Union[TimespecificParametersPreview, LegacyCheckParameters]:
        """Create a serializeable version for preview via automation call"""
        if self._is_constant():
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
        default: LegacyCheckParameters,
        timeperiod_values: Sequence[Tuple[TimeperiodName, LegacyCheckParameters]],
    ) -> None:
        # LegacyCheckParameters is almost as usefull as `object`.
        # I hope we end up with a more useful type at some point :-(
        self.default: Final = default
        self.timeperiod_values: Final = tuple(timeperiod_values)

    @classmethod
    def from_parameters(cls, parameters: LegacyCheckParameters) -> TimespecificParameterSet:
        if isinstance(parameters, dict) and "tp_default_value" in parameters:
            return cls(parameters["tp_default_value"], parameters["tp_values"])
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
    ) -> Iterable[LegacyCheckParameters]:
        for timeperiod_name, tp_entry in self.timeperiod_values:
            try:
                if is_active(timeperiod_name):
                    yield tp_entry
            except Exception:
                # Connection error
                if cmk.utils.debug.enabled():
                    raise
                return

    def evaluate(self, is_active: _IsTimeperiodActiveCallback) -> LegacyCheckParameters:
        return boil_down_parameters(self._active_subsets(is_active), self.default)


def boil_down_parameters(
    parameters: Iterable[LegacyCheckParameters],
    default: LegacyCheckParameters,
) -> LegacyCheckParameters:
    """
    first occurrance wins:
    >>> boil_down_parameters([{'a': 1},{'a': 2, 'b': 3}], {})
    {'a': 1, 'b': 3}

    first non-Mapping wins:
    >>> boil_down_parameters([{'a': 1}, (23, 42), {'a': 2, 'b': 3}, (0, 42)], {})
    (23, 42)

    """
    merged: dict[str, Any] = {}
    for par in parameters:
        if not isinstance(par, dict):
            return par
        merged.update((item for item in par.items() if item[0] not in merged))

    try:
        # TODO: We could get rid of the suppression if we used a "isinstance(default, Mapping)"
        # guard, but it's a bit unclear how this affects performance.
        return {**default, **merged}  # type: ignore[list-item]
    except TypeError:
        return merged or default
