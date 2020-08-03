#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Tuple

from ..agent_based_api.v0 import render


def normalize_levels(
    mode: str,
    warn: Optional[float],
    crit: Optional[float],
    total: float,
    _perc_total: Optional[float] = None,
    render_unit: int = 1,
) -> Tuple[Optional[float], Optional[float], str]:
    """get normalized levels and formatter

    Levels may be given either as
     * Absolute levels on used
     * Absolute levels on free
     * Percentage levels on used
     * Percentage levels on free
    Normalize levels to absolute posive levels and return formatted levels text

        >>> normalize_levels("perc_used", 12, 42, 200)
        (24.0, 84.0, 'warn/crit at 12.0%/42.0% used')

    """
    # TODO: remove this weird case of different reference values.
    if _perc_total is None:
        _perc_total = total

    if warn is None or crit is None:
        return None, None, ""

    mode_split = mode.split('_', 1)
    if mode_split[0] not in ('perc', 'abs') or mode_split[-1] not in ('used', 'free'):
        raise NotImplementedError("unknown levels mode: %r" % (mode,))

    # normalize percent -> absolute
    if mode.startswith("perc"):
        warn_used = warn / 100.0 * _perc_total
        crit_used = crit / 100.0 * _perc_total
        levels_text = "%s/%s" % (render.percent(warn), render.percent(crit))
    else:  # absolute
        warn_used = float(warn)
        crit_used = float(crit)
        levels_text = "%s/%s" % (render.bytes(warn * render_unit), render.bytes(crit * render_unit))

    # normalize free -> used
    if mode.endswith("free"):
        warn_used = float(total - warn_used)
        crit_used = float(total - crit_used)
        levels_text = "warn/crit below %s free" % levels_text
    else:  # used
        levels_text = "warn/crit at %s used" % levels_text

    return warn_used, crit_used, levels_text
