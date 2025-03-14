#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.user import UserId

from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import MultipleChoice, MultipleChoiceElement


@pytest.fixture(scope="module", name="multiple_choice_spec")
def spec() -> MultipleChoice:
    return MultipleChoice(
        elements=[
            MultipleChoiceElement(name="foo", title=Title("foo")),
            MultipleChoiceElement(name="bar", title=Title("bar")),
            MultipleChoiceElement(name="baz", title=Title("baz")),
        ],
    )


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
def test_multiple_choice(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    data_origin: DataOrigin,
    multiple_choice_spec: MultipleChoice,
) -> None:
    # Note: custom sorting will be implemented with MultipleChoiceExpanded
    good_choices = ["foo", "bar"]
    sorted_good_choices = sorted(good_choices)
    visitor = get_visitor(multiple_choice_spec, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(good_choices)
    # Send good choice to vue
    assert vue_value == sorted_good_choices

    # No validation problems
    validation_messages = visitor.validate(good_choices)
    assert len(validation_messages) == 0

    # Write choice back to disk
    assert visitor.to_disk(good_choices) == sorted_good_choices


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
def test_multiple_choice_with_invalid_key(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    data_origin: DataOrigin,
    multiple_choice_spec: MultipleChoice,
) -> None:
    # Note: custom sorting will be implemented with MultipleChoiceExpanded
    # Check behaviour: Invalid keys are filtered out during parsing
    some_bad_choice = ["foo", "bar", "unknown_value"]
    some_bad_choice_filtered = ["bar", "foo"]
    visitor = get_visitor(multiple_choice_spec, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(some_bad_choice)
    # Send good choice to vue
    assert vue_value == some_bad_choice_filtered

    # No validation problems
    validation_messages = visitor.validate(some_bad_choice)
    assert len(validation_messages) == 0

    # Write choice back to disk
    assert visitor.to_disk(some_bad_choice) == some_bad_choice_filtered
