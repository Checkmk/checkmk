#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.valuespec import Age, Alternative, FixedValue, Float, Integer, Tuple, ValueSpec


def _NoLevels() -> FixedValue:
    return FixedValue(
        value=None,
        title=_("No Levels"),
        totext=_("Do not impose levels, always be OK"),
    )


_Spec = type[Integer] | type[Float] | type[Age]


def _FixedLevels(
    spec: _Spec,
    default_value: tuple[float | int, float | int],
    unit: str,
    direction: Literal["upper", "lower"],
) -> Tuple:
    def element(idx: Literal[0, 1], title_upper: str, title_lower: str) -> ValueSpec:
        title = title_upper if direction == "upper" else title_lower
        dv = default_value[idx]
        if issubclass(spec, Integer):
            return spec(title=title, default_value=int(dv), unit=unit)
        if issubclass(spec, Float):
            return spec(title=title, default_value=float(dv), unit=unit)
        if issubclass(spec, Age):
            return spec(title=title, default_value=int(dv))
        raise ValueError(f"illegal ValueSpec type {spec}, expected Integer or Float or Age")

    return Tuple(
        title=_("Fixed Levels"),
        elements=[
            element(0, _("Warning at"), _("Warning below")),
            element(1, _("Critical at"), _("Critical below")),
        ],
    )


def SimpleLevels(
    spec: _Spec = Float,
    help: str | None = None,
    default_levels: tuple[float | int, float | int] = (0.0, 0.0),
    default_value: tuple[float, float] | None = None,
    title: str | None = None,
    unit: str | None = None,
    direction: Literal["upper", "lower"] = "upper",
) -> Alternative:
    """
    Internal API. Might change between versions

    See Also:
        :func: cmk.gui.plugins.wato.utils.Levels
    """
    return Alternative(
        title=title,
        help=help,
        elements=[
            _NoLevels(),
            _FixedLevels(spec, default_value=default_levels, unit=unit or "", direction=direction),
        ],
        match=lambda v: 0 if v is None else 1,
        default_value=default_value,
    )
