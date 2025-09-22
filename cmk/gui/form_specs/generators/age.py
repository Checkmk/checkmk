#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence

from cmk.gui.form_specs.private.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import TimeMagnitude, TimeSpan


def Age(
    title: Title | None,
    label: Label,
    displayed_magnitudes: Sequence[TimeMagnitude] | None,
    custom_validate: Sequence[Callable[[float], None]] | None,
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    def float_to_int(value: object) -> int:
        assert isinstance(value, float)
        return int(value)

    def int_to_float(value: object) -> float:
        assert isinstance(value, int)
        return float(value)

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=TimeSpan(
            title=title,
            label=label,
            displayed_magnitudes=displayed_magnitudes
            or [TimeMagnitude.DAY, TimeMagnitude.HOUR, TimeMagnitude.MINUTE, TimeMagnitude.SECOND],
            custom_validate=custom_validate,
        ),
        to_disk=float_to_int,
        from_disk=int_to_float,
    )
