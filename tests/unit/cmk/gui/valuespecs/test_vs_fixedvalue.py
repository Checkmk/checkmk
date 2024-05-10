#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success

Sentinel = object()


class TestValueSpecFixedValue:
    def test_validate(self) -> None:
        expect_validate_success(vs.FixedValue(1), 1)
        expect_validate_failure(vs.FixedValue(1), 2)

    def test_value_to_html(self) -> None:
        assert vs.FixedValue(value=1).value_to_html(1) == "1"
        assert vs.FixedValue(value=1, totext="eins").value_to_html(1) == "eins"
        assert vs.FixedValue(value="zwei").value_to_html("zwei") == "zwei"
        assert vs.FixedValue(value="zwei").value_to_html("drei") == "drei"

    def test_from_html_vars(self, request_context: None) -> None:
        assert vs.FixedValue(value=Sentinel).from_html_vars("") is Sentinel

    def test_mask(self) -> None:
        assert vs.FixedValue(value=2).mask(1) == 1

    def test_default(self) -> None:
        assert vs.FixedValue(value=2).default_value() == 2
        assert vs.FixedValue(value=2).canonical_value() == 2
        # Does this make sense? I don't think so:
        assert vs.FixedValue(value=2, default_value=3).default_value() == 3

    def test_json(self) -> None:
        assert vs.FixedValue(value=2).value_to_json(1) == 1
        assert vs.FixedValue(value=2).value_from_json(1) == 1
