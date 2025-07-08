#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs.private import ListUniqueSelection, SingleChoiceElementExtended
from cmk.gui.form_specs.private.list_unique_selection import UniqueSingleChoiceElement
from cmk.gui.form_specs.vue import get_visitor, IncomingData, RawDiskData, RawFrontendData
from cmk.gui.form_specs.vue.visitors import (
    SingleChoiceVisitor,
)

from cmk.rulesets.v1 import Title


@pytest.fixture(scope="module", name="list_unique_selection_spec")
def spec() -> ListUniqueSelection:
    return ListUniqueSelection(
        elements=[
            UniqueSingleChoiceElement(
                parameter_form=SingleChoiceElementExtended(
                    name="foo",
                    title=Title("Foo"),
                )
            ),
            UniqueSingleChoiceElement(
                unique=False,
                parameter_form=SingleChoiceElementExtended(
                    name="bar",
                    title=Title("Bar"),
                ),
            ),
        ],
    )


@pytest.mark.parametrize(
    ["value", "expected_value"],
    [
        (
            RawDiskData(["foo", "bar"]),
            [SingleChoiceVisitor.option_id("foo"), SingleChoiceVisitor.option_id("bar")],
        ),
    ],
)
def test_list_unique_selection_visitor_to_vue(
    value: IncomingData,
    expected_value: list[str],
    list_unique_selection_spec: ListUniqueSelection,
) -> None:
    visitor = get_visitor(list_unique_selection_spec)
    vue_value = visitor.to_vue(value)[1]
    assert vue_value == expected_value
    assert len(visitor.validate(value)) == 0


@pytest.mark.parametrize(
    ["value", "expected_value"],
    [
        (
            RawFrontendData(
                [SingleChoiceVisitor.option_id("foo"), SingleChoiceVisitor.option_id("bar")]
            ),
            ["foo", "bar"],
        ),
    ],
)
def test_list_unique_selection_visitor_to_disk(
    value: IncomingData,
    expected_value: list[str],
    list_unique_selection_spec: ListUniqueSelection,
) -> None:
    visitor = get_visitor(list_unique_selection_spec)
    disk_value = visitor.to_disk(value)
    assert disk_value == expected_value
    assert len(visitor.validate(value)) == 0
