#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.utils.parameters import boil_down_parameters


def _all_dicts() -> Sequence[Mapping[str, str]]:
    return [{"key": "first_value"}, {"key": "second_value"}, {"key2": "some_value"}]


def _with_tuple() -> Sequence[Mapping[object, object] | tuple[object, object]]:
    return [(23, 23), {"key": "first_value"}, (666, 666)]


def test_boil_down_parameters_good_case() -> None:
    assert boil_down_parameters(_all_dicts(), {"default": "some_value"}) == {
        "key": "first_value",
        "key2": "some_value",
        "default": "some_value",
    }
    assert boil_down_parameters(_all_dicts(), None) == {
        "key": "first_value",
        "key2": "some_value",
    }


def test_boil_down_parameters_first_tuple_wins() -> None:
    assert boil_down_parameters(_with_tuple(), (42, 42)) == (23, 23)
    assert boil_down_parameters((), (42, 42)) == (42, 42)


def test_boil_down_parameters_default_is_tuple() -> None:
    assert boil_down_parameters((), (42, 42)) == (42, 42)
    assert boil_down_parameters(_all_dicts(), (42, 42)) == {
        "key": "first_value",
        "key2": "some_value",
    }
