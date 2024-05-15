#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.parameters import merge_parameters


def test_merge_parameters_merges() -> None:
    assert merge_parameters(
        (
            {"first": "first_value"},
            {"second": "second_value"},
        ),
        {"default": "default_value"},
    ) == {
        "first": "first_value",
        "second": "second_value",
        "default": "default_value",
    }


def test_merge_parameters_first_wins() -> None:
    assert merge_parameters(({"a": "first"}, {"a": "second"}), {"a": "default"}) == {"a": "first"}
