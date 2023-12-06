#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.valuespec import Age, Alternative, FixedValue, Float, Integer, Percentage, Tuple


def _NoLevels() -> FixedValue:
    return FixedValue(
        value=None,
        title=_("No Levels"),
        totext=_("Do not impose levels, always be OK"),
    )


_Spec = type[Integer] | type[Float] | type[Percentage] | type[Age]


def _FixedLevels(
    value_spec: _Spec,
    default_value: tuple[float | int, float | int],
    unit: str,
    direction: Literal["upper", "lower"],
) -> Tuple:
    type_ = int if value_spec in (Integer, Age) else float
    kw = {} if value_spec is Age else {"unit": unit}
    return Tuple(
        title=_("Fixed Levels"),
        elements=[
            value_spec(
                title=_("Warning at") if direction == "upper" else _("Warning below"),
                default_value=type_(default_value[0]),
                **kw,  # type: ignore[arg-type]
            ),
            value_spec(
                title=_("Critical at") if direction == "upper" else _("Critical below"),
                default_value=type_(default_value[1]),
                **kw,  # type: ignore[arg-type]
            ),
        ],
    )


def SimpleLevels(
    spec: _Spec = Float,
    help: str | None = None,  # pylint: disable=redefined-builtin
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
