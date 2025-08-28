#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.form_specs.vue import DEFAULT_VALUE, get_visitor, VisitorOptions
from cmk.rulesets.v1.form_specs import CascadingSingleChoice

CascadingElementSelectionTypes = str | int | None | bool
CascadingElementUseFormSpec = bool
CascadingElementValueMapping = dict[
    str, tuple[CascadingElementSelectionTypes, CascadingElementUseFormSpec]
]


def _get_type_of_object_as_string(value: object) -> str:
    """
    Returns a string representation of the type of the given object.
    This is used to create a mapping for the CascadingSingleChoice elements.
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, tuple):
        return f"tuple[{', '.join(_get_type_of_object_as_string(v) for v in value)}]"
    if isinstance(value, dict):
        return "dict"
    raise TypeError(f"Unsupported type: {type(value)}")


def enable_deprecated_alternative(
    wrapped_form_spec: CascadingSingleChoice,
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    # Basic idea:
    # The CascadingSingleChoice elements should have "1", "2", "3", etc. as name.
    # Determine the default value of each element
    # The types are extracted from the data structure and transformed into an identifier which is used for mapping
    # Goal: A map with the following structure:
    # Example mapping for a CascadingSingleChoice with 7 elements:
    # {
    #     "int": "alternative1"
    #     "str": "alternative2",
    #     "tuple[str, str]": "alternative3",
    #     "tuple[float, float]": "alternative4",
    #     "bool": "alternative5",
    #     "None": "alternative6"
    #     "dict": "alternative7",
    # }
    # This can't be waterproof, but it should be sufficient for the most common cases.

    mapping: dict[str, str] = {}
    for element in wrapped_form_spec.elements:
        visitor = get_visitor(
            element.parameter_form, VisitorOptions(migrate_values=False, mask_values=False)
        )
        name_for_type = _get_type_of_object_as_string(visitor.to_vue(DEFAULT_VALUE)[1])
        mapping[name_for_type] = element.name

    def to_disk(value: object) -> object:
        assert isinstance(value, tuple) and len(value) == 2
        return value[1]

    def from_disk(value: object) -> tuple[str, Any]:
        name_for_type = _get_type_of_object_as_string(value)
        return mapping[name_for_type], value

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=wrapped_form_spec,
        from_disk=from_disk,
        to_disk=to_disk,
    )
