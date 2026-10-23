#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import TemperatureUnit
from cmk.gui.i18n import _

__all__ = ["TemperatureUnit", "temperature_unit_choices"]


def temperature_unit_choices() -> list[tuple[str, str]]:
    return [
        (TemperatureUnit.CELSIUS.value, _("Degree Celsius")),
        (TemperatureUnit.FAHRENHEIT.value, _("Degree Fahrenheit")),
    ]
