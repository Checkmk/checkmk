#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

import pytest

from cmk.gui.form_specs.private import ListExtended
from cmk.gui.form_specs.vue import (
    DEFAULT_VALUE,
    get_visitor,
    IncomingData,
    RawDiskData,
    RawFrontendData,
)
from cmk.gui.form_specs.vue.visitors import (
    SingleChoiceVisitor,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    List,
    SingleChoice,
    SingleChoiceElement,
)


@pytest.fixture(name="spec")
def list_spec() -> List:
    return ListExtended(
        element_template=SingleChoice(
            title=Title("single choice"),
            elements=[
                SingleChoiceElement(name="choice1", title=Title("Choice 1")),
                SingleChoiceElement(name="choice2", title=Title("Choice 2")),
            ],
            prefill=DefaultValue("choice1"),
        ),
        prefill=DefaultValue(["choice1", "choice2"]),
    )


@pytest.mark.parametrize(
    ["value", "expected_frontend_value", "expected_disk_value"],
    [
        pytest.param(
            DEFAULT_VALUE,
            [
                SingleChoiceVisitor.option_id("choice1"),
                SingleChoiceVisitor.option_id("choice2"),
            ],
            ["choice1", "choice2"],
            id="ListExtended overwrites DefaultValue",
        ),
        [
            RawFrontendData([SingleChoiceVisitor.option_id("choice1")]),
            [SingleChoiceVisitor.option_id("choice1")],
            ["choice1"],
        ],
        [
            RawDiskData(["choice1"]),
            [SingleChoiceVisitor.option_id("choice1")],
            ["choice1"],
        ],
    ],
)
def test_list(
    spec: ListExtended,
    value: IncomingData,
    expected_frontend_value: list[Any],
    expected_disk_value: list[Any],
) -> None:
    visitor = get_visitor(spec)
    assert visitor.validate(value) == []
    assert visitor.to_vue(value)[1] == expected_frontend_value
    assert visitor.to_disk(value) == expected_disk_value
