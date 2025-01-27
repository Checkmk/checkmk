#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from typing import Any

import pytest

import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success, request_var

CHOICES: Sequence[vs.ListChoiceChoice] = [
    (1, "eins"),
    (2, "zwei"),
    (3, "drei"),
]


def _get_list_choice(**arguments: Any) -> vs.ListChoice:
    class _LC(vs.ListChoice):
        def get_elements(self) -> Sequence[vs.ListChoiceChoice]:
            return CHOICES

    return _LC(**arguments)


def _load_elements(lc: vs.ListChoice) -> Sequence[vs.ListChoiceChoice]:
    lc.load_elements()
    return lc._elements


class TestListChoice:
    def test_load_elements(self):
        assert _load_elements(_get_list_choice()) == CHOICES
        assert _load_elements(vs.ListChoice(choices=CHOICES)) == CHOICES
        assert _load_elements(vs.ListChoice(choices=lambda: CHOICES)) == CHOICES
        assert _load_elements(vs.ListChoice(choices=dict(CHOICES))) == [
            ("1", "1 - eins"),
            ("2", "2 - zwei"),
            ("3", "3 - drei"),
        ]

        with pytest.raises(ValueError, match="illegal type for choices"):
            _load_elements(vs.ListChoice(choices=123))  # type: ignore[arg-type]

    def test_validate(self):
        expect_validate_success(_get_list_choice(), [1, 2])
        expect_validate_success(_get_list_choice(), [])
        expect_validate_failure(_get_list_choice(allow_empty=False), [])
        expect_validate_failure(_get_list_choice(), ["zwei"])
        expect_validate_failure(_get_list_choice(), "not a list")

    def test_json(self):
        assert _get_list_choice().value_to_json([1, 2]) == [1, 2]
        assert _get_list_choice().value_from_json([1, 2]) == [1, 2]

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(l_0="on", l_2="on"):
            assert _get_list_choice().from_html_vars("l") == [1, 3]

    def test_mask(self):
        assert _get_list_choice().mask(["2"]) == ["2"]

    def test_canonical_value(self):
        assert not _get_list_choice().canonical_value()
