#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import NonConvertibleUnit, notation_name, precision_kind, Unit
from cmk.shared_typing.cmk_time_series_graph import Precision as SharedPrecision
from cmk.shared_typing.cmk_time_series_graph import UnitFormat


def unit_to_unit_format(unit: Unit | NonConvertibleUnit) -> UnitFormat:
    return UnitFormat(
        notation=notation_name(unit.notation),
        symbol=unit.notation.symbol,
        precision=SharedPrecision(
            type=precision_kind(unit.precision), digits=unit.precision.digits
        ),
        convertible=None if isinstance(unit, Unit) else False,
    )
