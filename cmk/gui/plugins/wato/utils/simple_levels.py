#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from functools import partial
from typing import Optional, Protocol
from typing import Tuple as _Tuple

from cmk.gui.i18n import _
from cmk.gui.valuespec import Alternative, FixedValue, Float, Tuple


def _NoLevels() -> FixedValue:
    return FixedValue(
        value=None,
        title=_("No Levels"),
        totext=_("Do not impose levels, always be OK"),
    )


class _Spec(Protocol):
    def __call__(self, title: str, default_value: float):
        ...


def _FixedLevels(
    value_spec: _Spec,
    default_value: _Tuple[float, float],
) -> Tuple:
    return Tuple(
        title=_("Fixed Levels"),
        elements=[
            value_spec(
                title=_("Warning at"),
                default_value=default_value[0],
            ),
            value_spec(
                title=_("Critical at"),
                default_value=default_value[1],
            ),
        ],
    )


def SimpleLevels(
    spec: _Spec = Float,
    help: Optional[str] = None,  # pylint: disable=redefined-builtin
    default_levels: _Tuple[float, float] = (0.0, 0.0),
    default_value: Optional[_Tuple[float, float]] = None,
    title: Optional[str] = None,
    unit: Optional[str] = None,
) -> Alternative:
    """
    Internal API. Might change between versions

    See Also:
        :func: cmk.gui.plugins.wato.utils.Levels
    """

    def match_levels_alternative(v: Optional[_Tuple[float, float]]) -> int:
        if v is None:
            return 0
        return 1

    if unit is not None:
        spec = partial(spec, unit=unit)

    elements = [
        _NoLevels(),
        _FixedLevels(spec, default_value=default_levels),
    ]
    return Alternative(
        title=title,
        help=help,
        elements=elements,
        match=match_levels_alternative,
        default_value=default_value,
    )
