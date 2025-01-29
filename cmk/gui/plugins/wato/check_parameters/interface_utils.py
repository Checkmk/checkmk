#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for interface check parameter module internals"""

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import PredictiveLevels
from cmk.gui.valuespec import CascadingDropdown, Integer, Migrate, Percentage, Tuple, ValueSpec


def _perc_levels() -> Tuple:
    return Tuple(
        orientation="float",
        show_titles=False,
        elements=[
            Percentage(label=_("Warning at")),
            Percentage(label=_("Critical at")),
        ],
    )


def _abs_levels() -> Tuple:
    return Tuple(
        orientation="float",
        show_titles=False,
        elements=[
            Integer(label=_("Warning at")),
            Integer(label=_("Critical at")),
        ],
    )


def _upper_lower_dropwdown(levels_vs: ValueSpec) -> CascadingDropdown:
    return CascadingDropdown(
        orientation="horizontal",
        choices=[
            ("upper", _("Upper"), levels_vs),
            ("lower", _("Lower"), levels_vs),
        ],
    )


def vs_interface_traffic():
    return Migrate(
        CascadingDropdown(
            orientation="horizontal",
            choices=[
                (
                    "abs",
                    _("Absolute levels in bits or bytes per second"),
                    _upper_lower_dropwdown(_abs_levels()),
                ),
                (
                    "perc",
                    _("Percentual levels (in relation to port speed)"),
                    _upper_lower_dropwdown(_perc_levels()),
                ),
                (
                    "predictive",
                    _("Predictive levels (only on CMC)"),
                    PredictiveLevels(),
                ),
            ],
        ),
        migrate=_migrate,
    )


def _migrate(p: tuple[str, object]) -> tuple[str, object]:
    """
    >>> _migrate(('abs', ('upper', (1000, 2000))))
    ('abs', ('upper', (1000, 2000)))
    >>> _migrate(('predictive', {'horizon': 90, 'levels_upper': ('absolute', (2.0, 4.0)), 'period': 'wday'}))
    ('predictive', {'horizon': 90, 'levels_upper': ('absolute', (2.0, 4.0)), 'period': 'wday'})
    >>> _migrate(('lower', ('perc', (50.0, 75.0))))
    ('perc', ('lower', (50.0, 75.0)))
    >>> _migrate(('upper', ('predictive', {'horizon': 90, 'levels_upper': ('absolute', (2.0, 4.0)), 'period': 'wday'})))
    ('predictive', {'horizon': 90, 'levels_upper': ('absolute', (2.0, 4.0)), 'period': 'wday'})
    """
    if p[0] in ("abs", "perc", "predictive"):
        return p
    upper_or_lower, level_spec = p
    assert isinstance(level_spec, tuple)
    if level_spec[0] == "predictive":
        return level_spec[0], level_spec[1]
    return level_spec[0], (upper_or_lower, level_spec[1])
