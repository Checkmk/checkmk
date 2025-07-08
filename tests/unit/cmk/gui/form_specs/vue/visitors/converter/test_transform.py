#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.form_specs.vue import get_visitor, RawDiskData, RawFrontendData

from cmk.rulesets.v1.form_specs import Integer


def _add5(value: object) -> int:
    assert isinstance(value, int), "Soothe mypy"
    return value + 5


def _subtract5(value: object) -> int:
    assert isinstance(value, int), "Soothe mypy"
    return value - 5


def test_transform_to_disk() -> None:
    spec = TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=Integer(),
        from_disk=_add5,
        to_disk=_subtract5,
    )

    visitor = get_visitor(spec)

    assert visitor.to_disk(RawFrontendData(5)) == 0
    assert visitor.to_disk(RawDiskData(0)) == 0


def test_transform_to_vue() -> None:
    spec = TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=Integer(),
        from_disk=_add5,
        to_disk=_subtract5,
    )

    visitor = get_visitor(spec)

    assert visitor.to_vue(RawFrontendData(0))[1] == 0
    assert visitor.to_vue(RawDiskData(0))[1] == 5
