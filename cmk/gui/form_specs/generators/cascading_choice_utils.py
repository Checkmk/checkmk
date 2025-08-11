#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.rulesets.v1.form_specs import CascadingSingleChoice

CascadingElementSelectionTypes = str | int | None | bool


@dataclass
class CascadingDataConversion:
    name_in_form_spec: str
    value_on_disk: CascadingElementSelectionTypes
    has_form_spec: bool


CascadingElementValueMapping = dict[str, CascadingDataConversion]


def enable_deprecated_cascading_elements(
    wrapped_form_spec: CascadingSingleChoice,
    special_value_mapping: Sequence[CascadingDataConversion],
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    mapping = {v.name_in_form_spec: v for v in special_value_mapping}
    reversed_mapping = {v.value_on_disk: v for v in special_value_mapping}

    def to_disk(value: object) -> object:
        assert isinstance(value, tuple) and len(value) == 2
        element_name, form_spec_value = value
        if (element_mapping := mapping.get(element_name)) is None:
            return value  # No conversion required

        if not element_mapping.has_form_spec:
            return element_mapping.value_on_disk
        return element_mapping.value_on_disk, form_spec_value

    def from_disk(value: object) -> tuple[str, Any]:
        assert isinstance(value, str | bool | int | tuple) or value is None
        if isinstance(value, tuple):
            first_element = value[0]
            if isinstance(first_element, str):
                # This value already uses the only valid format
                return first_element, value[1]

            selected_element = reversed_mapping[first_element].name_in_form_spec
            return selected_element, value[1]

        # A selection without a form spec
        return reversed_mapping[value].name_in_form_spec, True

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=wrapped_form_spec,
        from_disk=from_disk,
        to_disk=to_disk,
    )
