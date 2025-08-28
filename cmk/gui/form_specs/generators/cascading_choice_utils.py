#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.rulesets.v1.form_specs import CascadingSingleChoice

CascadingElementSelectionTypes = str | int | None | bool
CascadingElementUseFormSpec = bool
CascadingElementValueMapping = dict[
    str, tuple[CascadingElementSelectionTypes, CascadingElementUseFormSpec]
]


def enable_deprecated_cascading_elements(
    wrapped_form_spec: CascadingSingleChoice, cascading_value_mapping: CascadingElementValueMapping
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    reverse_selection_mapping = {v[0]: k for k, v in cascading_value_mapping.items()}

    def to_disk(value: object) -> object:
        assert isinstance(value, tuple) and len(value) == 2
        element_name, element_value = value
        wrapped_value, use_form_spec_value = cascading_value_mapping[element_name]
        if not use_form_spec_value:
            return wrapped_value
        return wrapped_value, element_value

    def from_disk(value: object) -> tuple[str, Any]:
        assert isinstance(value, str | bool | int | tuple) or value is None
        if isinstance(value, tuple):
            if isinstance(value[0], str):
                # This value is already in the new official format
                first_element = value[0]
                assert isinstance(first_element, str)
                return first_element, value[1]

            form_spec_name = reverse_selection_mapping[value[0]]
            return form_spec_name, value[1]

        # A selection without a form spec
        return reverse_selection_mapping[value], True

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=wrapped_form_spec,
        from_disk=from_disk,
        to_disk=to_disk,
    )
