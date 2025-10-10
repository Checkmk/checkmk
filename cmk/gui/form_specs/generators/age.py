#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence

from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import DefaultValue, InputHint, TimeMagnitude, TimeSpan


def Age(
    title: Title | None = None,
    label: Label | None = None,
    displayed_magnitudes: Sequence[TimeMagnitude] | None = None,
    custom_validate: Sequence[Callable[[float], None]] | None = None,
    prefill: DefaultValue[float] | None = None,
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    def float_to_int(value: object) -> int:
        assert isinstance(value, float)
        return int(value)

    def int_to_float(value: object) -> float:
        assert isinstance(value, int)
        return float(value)

    if displayed_magnitudes is None:
        displayed_magnitudes = [
            TimeMagnitude.DAY,
            TimeMagnitude.HOUR,
            TimeMagnitude.MINUTE,
            TimeMagnitude.SECOND,
        ]

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=TimeSpan(
            title=title,
            label=label,
            displayed_magnitudes=displayed_magnitudes,
            custom_validate=custom_validate,
            prefill=prefill or InputHint(value=0.0),
        ),
        to_disk=float_to_int,
        from_disk=int_to_float,
    )
