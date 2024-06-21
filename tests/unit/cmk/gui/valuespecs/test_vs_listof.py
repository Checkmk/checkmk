#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success, request_var


def get_list_of(**arguments: Any) -> vs.ListOf:
    return vs.ListOf(vs.Tuple([vs.Integer(), vs.Password()]), **arguments)


class TestListOf:
    def test_validate(self) -> None:
        expect_validate_success(get_list_of(), [])
        expect_validate_failure(get_list_of(allow_empty=False), [])
        expect_validate_success(get_list_of(), [(1, "1"), (2, "2")])
        expect_validate_failure(get_list_of(), [(1, "1"), (2, 2)])
        expect_validate_failure(get_list_of(), ((1, "1"),))

    def test_canonical_value(self) -> None:
        assert not get_list_of().canonical_value()

    def test_mask(self) -> None:
        assert get_list_of().mask([(1, "pwd")]) == [(1, "******")]

    def test_value_to_json(self) -> None:
        assert get_list_of().value_to_json([(1, "eins"), (2, "zwei")]) == [[1, "eins"], [2, "zwei"]]

    def test_from_json(self) -> None:
        assert get_list_of().value_from_json([[1, "eins"], [2, "zwei"]]) == [
            (1, "eins"),
            (2, "zwei"),
        ]

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(
            l_count="6",
            l_indexof_3="1",
            l_indexof_5="2",
            l_3_0="1",
            l_3_1="eins",
            l_5_0="2",
            l_5_1="zwei",
        ):
            assert get_list_of().from_html_vars("l") == [(1, "eins"), (2, "zwei")]
