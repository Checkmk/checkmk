#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import typing
from enum import Enum

from cmk.gui import valuespec
from cmk.gui.openapi.marshmallow_converter.type_defs import (
    maybe_lazy,
    V_c,
    ValuespecToValueMatchDict,
    ValuespecToValueMatchEntry,
    ValuespecToValueTransformFunction,
)
from cmk.gui.userdb._user_selection import _UserSelection
from cmk.gui.valuespec.definitions import _CAInput
from cmk.gui.wato import FullPathFolderChoice
from cmk.gui.wato._group_selection import _GroupSelection

MATCHERS: ValuespecToValueMatchDict[valuespec.ValueSpec] = {}


def match_on(
    vs_type: type[V_c] | type[None],
) -> typing.Callable[[ValuespecToValueTransformFunction], ValuespecToValueTransformFunction]:
    """Register a transform function based on value type.

    Acts as a decorator to register a transform function (`TransformFunction`) in
    a global matcher dictionary (`matchers`). The function associates the given
    `vs_type` with the provided transform function.

    Args:
        vs_type: Type of value to match on. Can be either a custom type `V_c` or `None`.

    Returns:
        Callable[[TransformFunction], TransformFunction]: A decorator that takes a
        transform function and returns it, after registering it in the global
        `matchers` dictionary.

    Example:
        @match_on(int)
        def transform_int(value):
            ...  # do stuff here

    """

    def register_func(func: ValuespecToValueTransformFunction) -> ValuespecToValueTransformFunction:
        if MATCHERS.get(vs_type):
            raise ValueError(f"Match function for {vs_type} already registered.")
        MATCHERS[vs_type] = ValuespecToValueMatchEntry(match_func=func)
        return func

    return register_func


def get_oneof_default_values(
    element: tuple[str, valuespec.ValueSpec],
) -> dict[str, typing.Any]:
    return {
        "type": element[0],
        "value": get_default_value(element[1]),
    }


@match_on(valuespec.Tuple)
def get_tuple_default_values(vs_instance: valuespec.Tuple) -> dict[str, typing.Any]:
    return {
        f"tuple_entry_{str(id_)}": get_default_value(vs)
        for id_, vs in enumerate(vs_instance._elements)
    }


@match_on(valuespec.Migrate)
@match_on(valuespec.Transform)
def get_transform_default_values(vs_instance: valuespec.Transform) -> typing.Any:
    return get_default_value(vs_instance._valuespec)


@match_on(valuespec.Alternative)
def get_alternative_default_values(
    vs_instance: valuespec.Alternative,
) -> typing.Any:
    return get_oneof_default_values(("alternative_option_0", vs_instance._elements[0]))


@match_on(valuespec.Dictionary)
def get_dict_default_values(vs_instance: valuespec.Dictionary) -> dict[str, typing.Any]:
    default_dict = {}
    for name, vs in maybe_lazy(vs_instance._elements):
        default_value = get_default_value(vs)
        if (
            default_value is not None
            and name in vs_instance._required_keys
            or not vs_instance._optional_keys
            or name in vs_instance._default_keys
        ):
            default_dict[name] = default_value
    return default_dict


@match_on(valuespec.CascadingDropdown)
def get_cascading_dropdown_default_values(
    vs_instance: valuespec.CascadingDropdown,
) -> typing.Any:
    elements = [
        (str(id_), vs_instance) for id_, _title, vs_instance in vs_instance.choices() if vs_instance
    ]
    return get_oneof_default_values(elements[0])


@match_on(valuespec.IconSelector)
def get_icon_selector_default_values(
    vs_instance: valuespec.IconSelector,
) -> typing.Any:
    def_value = vs_instance.default_value()
    if def_value is None:
        return {"type": "disabled"}
    if isinstance(def_value, str):
        return {"type": "enabled", "icon": def_value}
    return {"type": "enabled", "icon": def_value["icon"], "emblem": def_value["emblem"]}


@match_on(valuespec.FileUpload)
def get_file_upload_default_values(
    vs_instance: valuespec.FileUpload,
) -> typing.Any:
    def_value = vs_instance.default_value()
    if def_value is None:
        return {"type": "disabled"}
    if isinstance(def_value, bytes):
        return {"type": "raw", "raw_value": def_value}
    return {
        "type": "file",
        "name": def_value[0],
        "mimetype": def_value[1],
        "content": def_value[2],
    }


@match_on(_CAInput)
def get_ca_input_default_values(
    vs_instance: _CAInput,
) -> typing.Any:
    def_value = vs_instance.default_value()
    if def_value is None:
        return {"type": "disabled"}
    return {
        "type": "enabled",
        "address": def_value[0],
        "port": def_value[1],
        "content": def_value[2],
    }


@match_on(valuespec.Password)
def get_password_default_values(
    vs_instance: valuespec.Password,
) -> typing.Any:
    def_value = vs_instance.default_value()
    if (minLength := vs_instance._minlen) is not None and len(def_value) < minLength:
        return minLength * "*"
    return def_value


@match_on(valuespec.Float)
@match_on(valuespec.Percentage)
@match_on(valuespec.Filesize)
@match_on(valuespec.Integer)
def get_numeric_default_values(vs_instance: valuespec.Integer) -> typing.Any:
    def_value = vs_instance.default_value()
    if (minimum := vs_instance._bounds._lower) is not None and def_value < minimum:
        return minimum
    return def_value


@match_on(valuespec.DropdownChoice)
@match_on(valuespec.OptionalDropdownChoice)
@match_on(_GroupSelection)
@match_on(_UserSelection)
@match_on(FullPathFolderChoice)
def get_dropdown_default_values(vs_instance: valuespec.DropdownChoice) -> typing.Any:
    def_value = cleanup_default_value(vs_instance.default_value())
    return str(def_value)


def cleanup_default_value(value: typing.Any) -> typing.Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return {
            f"tuple_entry_{str(id_)}": cleanup_default_value(def_value)
            for id_, def_value in enumerate(value)
        }
    return value


def get_default_value(vs_instance: valuespec.ValueSpec) -> typing.Any:
    match_entry = MATCHERS.get(type(vs_instance))

    def_value = match_entry.match_func(vs_instance) if match_entry else vs_instance.default_value()

    return cleanup_default_value(def_value)
