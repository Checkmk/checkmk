#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.rulesets.internal.form_specs import (
    CascadingSingleChoiceElementExtended,
    CascadingSingleChoiceExtended,
    MultipleChoiceExtended,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, FixedValue, MultipleChoiceElement


def test_cascading_single_choice_extended_rejects_default_missing_from_static_elements() -> None:
    with pytest.raises(ValueError, match="Default element 'b'"):
        CascadingSingleChoiceExtended(
            elements=[
                CascadingSingleChoiceElementExtended(
                    name="a", title=Title("A"), parameter_form=FixedValue(value=None)
                )
            ],
            prefill=DefaultValue("b"),
        )


def test_cascading_single_choice_extended_accepts_default_missing_from_lazy_elements() -> None:
    CascadingSingleChoiceExtended(
        elements=lambda: [
            CascadingSingleChoiceElementExtended(
                name="a", title=Title("A"), parameter_form=FixedValue(value=None)
            )
        ],
        prefill=DefaultValue("b"),
    )


def test_multiple_choice_extended_rejects_prefill_missing_from_static_elements() -> None:
    with pytest.raises(ValueError, match="Invalid prefill element"):
        MultipleChoiceExtended(
            elements=[MultipleChoiceElement(name="a", title=Title("A"))],
            prefill=DefaultValue(["b"]),
        )


def test_multiple_choice_extended_accepts_prefill_missing_from_lazy_elements() -> None:
    MultipleChoiceExtended(
        elements=lambda: [MultipleChoiceElement(name="a", title=Title("A"))],
        prefill=DefaultValue(["b"]),
    )
