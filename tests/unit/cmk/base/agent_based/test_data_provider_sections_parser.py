#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable

import pytest

import cmk.utils.debug
from cmk.utils.type_defs import SectionName

from cmk.core_helpers.host_sections import HostSections

from cmk.base import crash_reporting
from cmk.base.agent_based.data_provider import SectionsParser
from cmk.base.api.agent_based.register.section_plugins import (
    AgentSectionPlugin,
    trivial_section_factory,
)
from cmk.base.sources.agent import AgentRawDataSection


def _section(name: str, parse_function: Callable) -> AgentSectionPlugin:
    """create a simple section for testing"""
    section = trivial_section_factory(SectionName(name))
    return section._replace(parse_function=parse_function)


class TestSectionsParser:
    @pytest.fixture
    def sections_parser(self) -> SectionsParser:
        return SectionsParser(
            host_sections=HostSections[AgentRawDataSection](
                sections={
                    SectionName("one"): [],
                    SectionName("two"): [],
                }
            )
        )

    @staticmethod
    def test_parse_function_called_once(sections_parser: SectionsParser) -> None:
        counter = iter((1,))
        section = _section("one", lambda x: next(counter))

        _ = sections_parser.parse(section)
        parsing_result = sections_parser.parse(section)

        assert parsing_result is not None
        assert parsing_result.data == 1

    @staticmethod
    def test_parsing_errors(monkeypatch, sections_parser: SectionsParser) -> None:

        monkeypatch.setattr(
            crash_reporting,
            "create_section_crash_dump",
            lambda **kw: "crash dump msg",
        )
        # Debug mode raises instead of creating the crash report that we want here.
        cmk.utils.debug.disable()
        section = _section("one", lambda x: 1 / 0)

        assert sections_parser.parse(section) is None
        assert len(sections_parser.parsing_errors) == 1
        assert sections_parser.parsing_errors[0].startswith(
            "Parsing of section one failed - please submit a crash report! (Crash-ID: "
        )

    @staticmethod
    def test_parse(sections_parser: SectionsParser) -> None:
        parsed_data = object()
        section = _section("one", lambda x: parsed_data)
        parsing_result = sections_parser.parse(section)

        assert parsing_result is not None
        assert parsing_result.data is parsed_data
        assert parsing_result.cache_info is None

    @staticmethod
    def test_disable(sections_parser: SectionsParser) -> None:
        section = _section("one", lambda x: 42)
        sections_parser.disable((SectionName("one"),))

        assert sections_parser.parse(section) is None

    @staticmethod
    def test_parse_missing_section(sections_parser: SectionsParser) -> None:
        missing_section = _section("missing_section", lambda x: 42)  # function does not matter

        assert sections_parser.parse(missing_section) is None

    @staticmethod
    def test_parse_section_returns_none(sections_parser: SectionsParser) -> None:
        section = _section("one", lambda x: None)

        assert sections_parser.parse(section) is None
