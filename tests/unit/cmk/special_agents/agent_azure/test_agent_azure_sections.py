#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.special_agents.agent_azure import Section


class TestSection:
    @pytest.fixture
    def name(self):
        return "testsection"

    @pytest.fixture
    def piggytargets(self):
        return ["one"]

    @pytest.fixture
    def seperator(self):
        return 1

    @pytest.fixture
    def options(self):
        return ["myopts"]

    @pytest.mark.parametrize(
        "piggytarget, expected_piggytarget_header",
        [
            (["one"], "<<<<one>>>>"),
            (["piggy-back"], "<<<<piggy-back>>>>"),
        ],
    )
    def test_piggytarget_header(
        self,
        name,
        piggytarget,
        expected_piggytarget_header,
        seperator,
        options,
        capsys,
    ):
        section = Section(name, piggytarget, seperator, options)
        section.add("blah")
        section.write()
        section_stdout = capsys.readouterr().out.split("\n")
        assert section_stdout[0] == expected_piggytarget_header

    @pytest.mark.parametrize(
        "section_name, expected_section_header",
        [
            ("testsection", "<<<testsection:sep(1):myopts>>>"),
            ("test-section", "<<<test_section:sep(1):myopts>>>"),
        ],
    )
    def test_section_header(
        self,
        section_name,
        expected_section_header,
        piggytargets,
        seperator,
        options,
        capsys,
    ):
        section = Section(section_name, piggytargets, seperator, options)
        section.add("blah")
        section.write()
        section_stdout = capsys.readouterr().out.split("\n")
        assert section_stdout[1] == expected_section_header
