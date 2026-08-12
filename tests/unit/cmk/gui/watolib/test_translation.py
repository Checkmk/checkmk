#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Pins that translation_form_spec_elements() and translation_elements() share one disk schema."""

from collections.abc import Sequence
from typing import Literal

import pytest

from cmk.gui.form_specs import DEFAULT_VALUE, get_visitor, RawDiskData, VisitorOptions
from cmk.gui.watolib.translation import translation_elements, translation_form_spec_elements
from cmk.rulesets.internal.form_specs import ListExtended, SingleChoiceExtended

_CASE_DISK_VALUES = (None, "lower", "upper")
_REGEX_DISK_VALUES: Sequence[list[tuple[str, str]]] = (
    [],
    [("vm_(.*)_prod", "\\1")],
    [("vm_(.*)_prod", "\\1"), ("(.*)", "\\1.example.org")],
)
_MAPPING_DISK_VALUES: Sequence[list[tuple[str, str]]] = (
    [],
    [("sourcename", "targetname")],
)

type _TranslationFormSpec = (
    SingleChoiceExtended[Literal["lower", "upper"] | None] | ListExtended[tuple[object, ...]]
)


def _form_specs_by_key() -> dict[str, _TranslationFormSpec]:
    return dict(translation_form_spec_elements())


def test_form_spec_and_valuespec_offer_the_same_elements() -> None:
    assert (
        [key for key, _form_spec in translation_form_spec_elements()]
        == [key for key, _valuespec in translation_elements()]
        == ["case", "regex", "mapping"]
    )


@pytest.mark.parametrize(
    "key, disk_values",
    [
        ("case", _CASE_DISK_VALUES),
        ("regex", _REGEX_DISK_VALUES),
        ("mapping", _MAPPING_DISK_VALUES),
    ],
)
def test_disk_value_is_accepted_by_both_and_round_trips(
    key: str, disk_values: Sequence[object]
) -> None:
    valuespec = dict(translation_elements())[key]
    visitor = get_visitor(
        _form_specs_by_key()[key],
        VisitorOptions(migrate_values=False, mask_values=False),
    )

    for disk_value in disk_values:
        valuespec.validate_datatype(disk_value, "")
        valuespec.validate_value(disk_value, "")
        assert not visitor.validate(RawDiskData(disk_value))
        assert visitor.to_disk(RawDiskData(disk_value)) == disk_value


def test_default_values_match() -> None:
    valuespecs = dict(translation_elements())
    for key, form_spec in _form_specs_by_key().items():
        visitor = get_visitor(form_spec, VisitorOptions(migrate_values=False, mask_values=False))
        assert visitor.to_disk(DEFAULT_VALUE) == valuespecs[key].default_value(), key
