#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.unstable import SingleChoiceExtended
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.gui.form_specs.vue import DEFAULT_VALUE, get_visitor, VisitorOptions
from cmk.rulesets.v1.form_specs import CascadingSingleChoice, FormSpec, SingleChoice


def _get_type_of_object_as_string(
    value: object, form_spec_type_hint: FormSpec[Any] | None = None
) -> str:
    """
    Returns a string representation of the type of the given object.
    This is used to create a mapping for the CascadingSingleChoice elements.
    """
    if value is None:
        return "None"
    if isinstance(form_spec_type_hint, SingleChoice | SingleChoiceExtended):
        return "str"
    if isinstance(form_spec_type_hint, Tuple) or isinstance(value, tuple):
        assert isinstance(value, tuple | list)
        return f"tuple[{', '.join(_get_type_of_object_as_string(v) for v in value)}]"
    if isinstance(value, bool):
        return f"bool:{value}"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
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

        # Try to determine the best fitting value
        # to_disk obviously returns the value as it would be stored on disk
        # since to_disk may raise a MKGeneralException with the DEFAULT_VALUE,
        # we use the to_vue method as fallback
        try:
            example_value_for_mapping = visitor.to_disk(DEFAULT_VALUE)
        except MKGeneralException:
            example_value_for_mapping = visitor.to_vue(DEFAULT_VALUE)[1]

        mapping[
            _get_type_of_object_as_string(
                example_value_for_mapping, form_spec_type_hint=element.parameter_form
            )
        ] = element.name

    def to_disk(value: object) -> object:
        assert isinstance(value, tuple) and len(value) == 2
        return value[1]

    def from_disk(value: object) -> tuple[str, Any]:
        return mapping[_get_type_of_object_as_string(value)], value

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=wrapped_form_spec,
        from_disk=from_disk,
        to_disk=to_disk,
    )
