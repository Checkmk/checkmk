#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs import DEFAULT_VALUE, get_visitor, VisitorOptions
from cmk.gui.form_specs.unstable import SingleChoiceExtended
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    DataSize,
    Float,
    FormSpec,
    Integer,
    Percentage,
    SingleChoice,
)


class _DeriveTypeError(Exception):
    pass


class _UnconvertableTypeError(Exception):
    pass


def _derive_type_from_form_spec(value: object, form_spec: FormSpec[Any]) -> str:
    if isinstance(form_spec, TransformDataForLegacyFormatOrRecomposeFunction):
        raise _UnconvertableTypeError(
            "Cannot derive type from TransformDataForLegacyFormatOrRecomposeFunction"
        )
    if isinstance(form_spec, SingleChoice | SingleChoiceExtended):
        # TODO: support other types
        return "str"
    if isinstance(form_spec, DataSize):
        return "int"
    if isinstance(form_spec, Tuple):
        tuple_tokens = []
        assert isinstance(value, tuple | list)
        for idx, element in enumerate(form_spec.elements):
            tuple_tokens.append(_derive_type(value[idx], form_spec=element))
        return f"tuple[{', '.join(tuple_tokens)}]"
    if isinstance(form_spec, Integer):
        return "int"
    if isinstance(form_spec, Float):
        return "float"
    if isinstance(form_spec, Percentage):
        return "float"
    raise _DeriveTypeError(
        f"Deprecated alternative: Cannot derive type from form spec: {form_spec.__class__.__name__}"
    )


def _derive_type_from_data(value: object) -> str:
    """
    Returns a string representation of the type of the given object.
    This is used to create a mapping for the CascadingSingleChoice elements.
    """
    if value is None:
        return "None"
    if isinstance(value, tuple):
        return f"tuple[{', '.join(_derive_type_from_data(v) for v in value)}]"
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
    raise _DeriveTypeError(f"Deprecated alternative: Unsupported data type: {type(value)}")


def _derive_type(value: object, form_spec: FormSpec[Any] | None = None) -> str:
    try:
        if form_spec is not None:
            return _derive_type_from_form_spec(value, form_spec)
        return _derive_type_from_data(value)
    except _DeriveTypeError:
        return _derive_type_from_data(value)


def enable_deprecated_alternative(
    wrapped_form_spec: CascadingSingleChoice,
    match_function: Callable[[Any], int] | None = None,
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
    if not match_function:
        for element in wrapped_form_spec.elements:
            visitor = get_visitor(
                element.parameter_form, VisitorOptions(migrate_values=False, mask_values=False)
            )
            try:
                example_value = visitor.to_disk(DEFAULT_VALUE)
            except MKGeneralException:
                example_value = visitor.to_vue(DEFAULT_VALUE)[1]

            try:
                mapping[_derive_type(example_value, element.parameter_form)] = element.name
            except (_DeriveTypeError, _UnconvertableTypeError):
                # This is the last resort. If we can not derive the type from the form spec
                # we use transform[Any] as fallback. When reading from disk and no other data matches,
                # this will be used. If the data can't be parsed by the chosen element, it will
                # report an error, anyway.
                if "transform[Any]" in mapping:
                    raise MKGeneralException(
                        f"Multiple elements with unconvertable types in CascadingSingleChoice {element} {wrapped_form_spec.title}"
                    )
                mapping["transform[Any]"] = element.name

    def to_disk(value: object) -> object:
        assert isinstance(value, tuple) and len(value) == 2
        return value[1]

    def from_disk(value: object) -> tuple[str, Any]:
        if match_function is not None:
            # If a match function is provided, use it to determine the correct element
            index = match_function(value)
            if index < 0 or index >= len(wrapped_form_spec.elements):
                raise MKGeneralException("Value does not match any alternative")
            return wrapped_form_spec.elements[index].name, value

        try:
            return mapping[_derive_type_from_data(value)], value
        except KeyError:
            if "transform[Any]" in mapping:
                return mapping["transform[Any]"], value

        raise MKGeneralException("Deprecated alternative: Unable to parse data from disk")

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=wrapped_form_spec,
        from_disk=from_disk,
        to_disk=to_disk,
    )
