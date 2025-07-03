#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs.private import ListOfStrings
from cmk.gui.form_specs.vue.visitors import get_visitor, RawDiskData, RawFrontendData

from cmk.rulesets.v1.form_specs import String


@pytest.fixture(scope="module", name="string_spec")
def spec() -> ListOfStrings:
    return ListOfStrings(string_spec=String())


@pytest.mark.parametrize("data_wrapper", [RawFrontendData, RawDiskData])
def test_list_of_strings_filter(
    data_wrapper: type[RawFrontendData | RawDiskData],
    string_spec: ListOfStrings,
) -> None:
    entries = data_wrapper(["foo", "", "bar", "baz", ""])
    visitor = get_visitor(string_spec)
    # Check filtering
    _vue_spec, vue_value = visitor.to_vue(entries)
    assert vue_value == ["foo", "bar", "baz"]

    # Check validation message
    validation_messages = visitor.validate(entries)
    assert len(validation_messages) == 0

    # Check data for disk
    assert visitor.to_disk(entries) == ["foo", "bar", "baz"]
