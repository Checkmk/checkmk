#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest  # type: ignore[import]

from cmk.utils.type_defs import SectionName

import cmk.base.data_sources.agent as agent


class TestSummarizer:
    pass


class TestParser:
    @pytest.mark.parametrize(
        "headerline, section_name, section_options",
        [
            (b"norris", SectionName("norris"), {}),
            (b"norris:chuck", SectionName("norris"), {"chuck": None}),
            (
                b"my_section:sep(0):cached(23,42)",
                SectionName("my_section"),
                {"sep": "0", "cached": "23,42"},
            ),
            (b"my.section:sep(0):cached(23,42)", None, {}),  # invalid section name
        ],
    )  # yapf: disable
    def test_parse_section_header(self, headerline, section_name, section_options):
        parsed_name, parsed_options = agent.Parser._parse_section_header(headerline)
        assert parsed_name == section_name
        assert parsed_options == section_options
