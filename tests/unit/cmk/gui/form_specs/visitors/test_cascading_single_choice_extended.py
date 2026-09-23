#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.form_specs import DEFAULT_VALUE, get_visitor, RawDiskData, VisitorOptions
from cmk.rulesets.internal.form_specs import (
    CascadingSingleChoiceElementExtended,
    CascadingSingleChoiceExtended,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, FixedValue
from cmk.shared_typing import vue_formspec_components as shared_type_defs

_VISITOR_OPTIONS = VisitorOptions(migrate_values=True, mask_values=False)


def _elements(*names: str) -> Sequence[CascadingSingleChoiceElementExtended[None]]:
    return [
        CascadingSingleChoiceElementExtended(
            name=name,
            title=Title("Choice"),
            parameter_form=FixedValue(value=None),
        )
        for name in names
    ]


def _validation_messages(spec: CascadingSingleChoiceExtended, value: RawDiskData) -> list[str]:
    return [m.message for m in get_visitor(spec, _VISITOR_OPTIONS).validate(value)]


def test_static_elements() -> None:
    spec = CascadingSingleChoiceExtended(elements=_elements("a"))

    assert _validation_messages(spec, RawDiskData(["a", None])) == []
    assert _validation_messages(spec, RawDiskData(["b", None])) == ["Invalid selection"]


def test_lazy_elements_are_resolved_on_every_visit() -> None:
    available = ["a"]
    spec = CascadingSingleChoiceExtended(elements=lambda: _elements(*available))

    assert _validation_messages(spec, RawDiskData(["b", None])) == ["Invalid selection"]

    available.append("b")

    assert _validation_messages(spec, RawDiskData(["b", None])) == []


def test_default_value_missing_from_lazy_elements_falls_back_to_input_hint() -> None:
    spec = CascadingSingleChoiceExtended(elements=lambda: _elements("a"), prefill=DefaultValue("b"))

    schema, value = get_visitor(spec, _VISITOR_OPTIONS).to_vue(DEFAULT_VALUE)

    assert value == ("", None)
    assert isinstance(schema, shared_type_defs.CascadingSingleChoice)
    assert schema.input_hint == "Please choose"
