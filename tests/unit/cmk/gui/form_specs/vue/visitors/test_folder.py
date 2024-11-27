#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private import Folder
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import DEFAULT_VALUE, VisitorOptions

from cmk.rulesets.v1 import Help, Title


@pytest.fixture(scope="module", name="folder_spec")
def spec() -> Folder:
    return Folder(
        title=Title("folder title"),
        help_text=Help("folder help"),
        input_hint="folder input hint",
    )


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    ["raw_value", "expected_value"],
    [
        [DEFAULT_VALUE, "folder input hint"],
        [""] * 2,
        ["some/folder/path"] * 2,
    ],
)
def test_folder_valid_value(
    folder_spec: Folder,
    data_origin: DataOrigin,
    raw_value: object,
    expected_value: str,
) -> None:
    visitor = get_visitor(folder_spec, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(raw_value)

    # Expected vue value
    assert vue_value == expected_value

    # Check validation messages - none for valid values
    validation_messages = visitor.validate(raw_value)
    assert len(validation_messages) == 0

    # Same value returned to disk
    assert visitor.to_disk(raw_value) == expected_value


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    "raw_value",
    [
        ["in_a_list"],
        ("in_a_tuple",),
        None,
    ],
)
def test_folder_invalid_data_type(
    folder_spec: Folder,
    data_origin: DataOrigin,
    raw_value: object,
) -> None:
    visitor = get_visitor(folder_spec, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(raw_value)

    # Expected vue value - empty string for invalid data type
    assert vue_value == ""

    # Check validation messages
    validation_messages = visitor.validate(raw_value)
    assert len(validation_messages) == 1

    # Invalid data type causes exception
    with pytest.raises(MKGeneralException):
        visitor.to_disk(raw_value)


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    ["raw_value", "expected_value"],
    [
        ["!@#$"] * 2,
        ["%^&*"] * 2,
        ["()_+"] * 2,
    ],
)
def test_folder_invalid_value(
    folder_spec: Folder,
    data_origin: DataOrigin,
    raw_value: str,
    expected_value: str,
) -> None:
    visitor = get_visitor(folder_spec, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(raw_value)

    # Expected vue value
    assert vue_value == expected_value

    # Check validation messages
    validation_messages = visitor.validate(raw_value)
    assert len(validation_messages) == 1

    # Same value returned to disk - valid data type, invalid value
    assert visitor.to_disk(raw_value) == expected_value
