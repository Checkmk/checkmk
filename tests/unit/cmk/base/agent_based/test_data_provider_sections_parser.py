#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from typing import Any

import pytest

from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import SectionMap, SectionName

from cmk.checkengine.parser import AgentRawDataSectionElem, HostSections
from cmk.checkengine.sectionparser import SectionsParser

from cmk.base.api.agent_based.register.section_plugins import trivial_section_factory

_ParseFunction = Callable[[Sequence[AgentRawDataSectionElem]], Any]


def _section(name: str, parse_function: Callable) -> tuple[SectionName, _ParseFunction]:
    """create a simple section for testing"""
    section = trivial_section_factory(SectionName(name))
    return section.name, parse_function


class TestSectionsParser:
    @pytest.fixture
    def sections_parser(self) -> SectionsParser[AgentRawDataSectionElem]:
        return SectionsParser[AgentRawDataSectionElem](
            host_sections=HostSections[SectionMap[AgentRawDataSectionElem]](
                sections={
                    SectionName("one"): [],
                    SectionName("two"): [],
                }
            ),
            host_name=HostName("only-neede-for-crash-reporting"),
            error_handling=lambda *args, **kw: "error",
        )

    @staticmethod
    def test_parse_function_called_once(
        sections_parser: SectionsParser[AgentRawDataSectionElem],
    ) -> None:
        counter = iter((1,))
        section_name, parse_function = _section("one", lambda x: next(counter))

        _ = sections_parser.parse(section_name, parse_function)
        parsing_result = sections_parser.parse(section_name, parse_function)

        assert parsing_result is not None
        assert parsing_result.data == 1

    @staticmethod
    @pytest.mark.usefixtures("disable_debug")
    def test_parsing_errors(
        sections_parser: SectionsParser[AgentRawDataSectionElem],
    ) -> None:
        section_name, parse_function = _section("one", lambda x: 1 / 0)

        assert sections_parser.parse(section_name, parse_function) is None
        assert len(sections_parser.parsing_errors) == 1
        assert sections_parser.parsing_errors == ["error"]

    @staticmethod
    def test_parse(sections_parser: SectionsParser[AgentRawDataSectionElem]) -> None:
        parsed_data = object()
        section_name, parse_function = _section("one", lambda x: parsed_data)
        parsing_result = sections_parser.parse(section_name, parse_function)

        assert parsing_result is not None
        assert parsing_result.data is parsed_data
        assert parsing_result.cache_info is None

    @staticmethod
    def test_disable(sections_parser: SectionsParser[AgentRawDataSectionElem]) -> None:
        section_name, parse_function = _section("one", lambda x: 42)
        sections_parser.disable([section_name])

        assert sections_parser.parse(section_name, parse_function) is None

    @staticmethod
    def test_parse_missing_section(
        sections_parser: SectionsParser[AgentRawDataSectionElem],
    ) -> None:
        section_name, parse_function = _section(
            "missing_section", lambda x: 42
        )  # function does not matter

        assert sections_parser.parse(section_name, parse_function) is None

    @staticmethod
    def test_parse_section_returns_none(
        sections_parser: SectionsParser[AgentRawDataSectionElem],
    ) -> None:
        section_name, parse_function = _section("one", lambda x: None)

        assert sections_parser.parse(section_name, parse_function) is None
