#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any


def scale_levels(
    p: None | tuple[float, float] | dict, factor: float
) -> None | tuple[float, float] | dict:
    if p is None:
        return None
    if isinstance(p, tuple):
        return p[0] * factor, p[1] * factor
    return scale_predictive(p, factor)


def scale_predictive(p: dict, factor: float) -> dict:
    """
    >>> from pprint import pprint
    >>> pprint(scale_predictive(
    ...     {
    ...         'period': 'minute',
    ...         'horizon': 4,
    ...         'levels_upper': ('absolute', (0.5, 1.0)),
    ...         'levels_lower': ('stdev', (2.0, 4.0)),
    ...     },
    ...     1024.0,
    ... ))
    {'horizon': 4,
     'levels_lower': ('stdev', (2.0, 4.0)),
     'levels_upper': ('absolute', (512.0, 1024.0)),
     'period': 'minute'}
    """
    return {k: _scale_predictive_element(k, v, factor) for k, v in p.items()}


def _scale_predictive_element(k: str, v: Any, factor: float) -> Any:
    match k:
        case "levels_upper" | "levels_lower":
            type_, (warn, crit) = v
            return (type_, (warn * factor, crit * factor) if type_ == "absolute" else (warn, crit))
        case "levels_upper_min":
            warn, crit = v
            return warn * factor, crit * factor
    return v
