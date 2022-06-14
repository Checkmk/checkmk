#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.sidebar.search import (
    ABCLabelMatchPlugin,
    HostLabelMatchPlugin,
    Label,
    ServiceLabelMatchPlugin,
)


class TestLabelMatchPlugin:
    def test_input_to_key_value_invalid_ok(self) -> None:
        assert ABCLabelMatchPlugin._input_to_key_value("key:value") == Label("key", "value", False)

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "",
            "abc",
            ":abc",
            "abc:",
        ],
    )
    def test_input_to_key_value_invalid(self, invalid_input: str) -> None:
        with pytest.raises(MKUserError):
            ABCLabelMatchPlugin._input_to_key_value(invalid_input)

    def test_get_livestatus_filters_no_input(self) -> None:
        assert HostLabelMatchPlugin().get_livestatus_filters("", {}) == ""

    def test_get_livestatus_filters_one_filter(self) -> None:
        assert (
            HostLabelMatchPlugin().get_livestatus_filters("hosts", {"hl": ["x:y"]})
            == "Filter: labels = 'x' 'y'\n"
        )

    def test_get_livestatus_filters_two_filters(self) -> None:
        assert (
            ServiceLabelMatchPlugin().get_livestatus_filters("services", {"sl": ["x:y", "a:b"]})
            == "Filter: labels = 'x' 'y'\nFilter: labels = 'a' 'b'\n"
        )
