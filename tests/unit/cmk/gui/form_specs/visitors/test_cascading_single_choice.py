#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    IncomingData,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    FixedValue,
    InputHint,
)


@pytest.fixture(name="spec")
def cascading_single_choice_spec(request: pytest.FixtureRequest) -> CascadingSingleChoice:
    """Fixture providing a CascadingSingleChoice spec with varying prefill values."""
    prefill = request.param
    return CascadingSingleChoice(
        title=Title("Cascading Single Choice"),
        elements=[
            CascadingSingleChoiceElement(
                name="choice1", title=Title("Choice 1"), parameter_form=FixedValue(value=None)
            ),
            CascadingSingleChoiceElement(
                name="choice2", title=Title("Choice 2"), parameter_form=FixedValue(value=None)
            ),
        ],
        prefill=prefill,
    )


@pytest.mark.parametrize(
    ["spec", "value", "expected_frontend_value", "expected_disk_value", "expected_validation"],
    [
        pytest.param(
            DefaultValue("choice1"),
            DEFAULT_VALUE,
            ("choice1", None),
            ("choice1", None),
            [],
            id="DEFAULT_VALUE with DefaultValue prefill",
        ),
        pytest.param(
            InputHint(Title("Please choose")),
            DEFAULT_VALUE,
            ("", None),
            ("", None),
            ["Prefill value is an input hint"],
            id="DEFAULT_VALUE with InputHint prefill",
        ),
        pytest.param(
            DefaultValue("choice1"),
            RawFrontendData(["choice1", None]),
            ("choice1", None),
            ("choice1", None),
            [],
            id="Frontend data with choice1",
        ),
        pytest.param(
            DefaultValue("choice1"),
            RawDiskData(["choice2", None]),
            ("choice2", None),
            ("choice2", None),
            [],
            id="Disk data with choice2",
        ),
    ],
    indirect=["spec"],
)
def test_cascading_single_choice(
    spec: CascadingSingleChoice,
    value: IncomingData,
    expected_frontend_value: tuple[str, object],
    expected_disk_value: tuple[str, object],
    expected_validation: list[str],
) -> None:
    """Test cascading single choice with various input values and prefill configurations."""
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))

    validation_messages = visitor.validate(value)
    assert [msg.message for msg in validation_messages] == expected_validation
    assert visitor.to_vue(value)[1] == expected_frontend_value

    if not expected_validation:
        assert visitor.to_disk(value) == expected_disk_value
