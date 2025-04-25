#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Sequence

import pytest

from cmk.ccc.hostaddress import HostName

from cmk.utils.sectionname import SectionMap, SectionName

from cmk.checkengine.discovery._host_labels import _all_parsing_results as all_parsing_results
from cmk.checkengine.fetcher import HostKey, SourceType
from cmk.checkengine.parser import AgentRawDataSection, AgentRawDataSectionElem, HostSections
from cmk.checkengine.sectionparser import _ParsingResult as ParsingResult
from cmk.checkengine.sectionparser import (
    ParsedSectionName,
    ParsedSectionsResolver,
    ResolvedResult,
    SectionPlugin,
    SectionsParser,
)


def _section(
    name: str, parsed_section_name: str, supersedes: set[str]
) -> tuple[SectionName, SectionPlugin]:
    return SectionName(name), SectionPlugin(
        supersedes={SectionName(n) for n in supersedes},
        parsed_section_name=ParsedSectionName(parsed_section_name),
        parse_function=lambda *args, **kw: object,
    )


class _FakeParser(dict):
    def parse(self, section_name: SectionName, *args: object) -> object:
        return self.get(str(section_name))

    def disable(self, names: Iterable[SectionName]) -> None:
        for name in names:
            _ = self.pop(str(name), None)


class TestParsedSectionsResolver:
    @staticmethod
    def make_provider(
        section_plugins: SectionMap[SectionPlugin],
    ) -> ParsedSectionsResolver:
        return ParsedSectionsResolver(
            _FakeParser(  # type: ignore[arg-type]
                {
                    "section_one": ParsingResult(data=1, cache_info=None),
                    "section_two": ParsingResult(data=2, cache_info=None),
                    "section_thr": ParsingResult(data=3, cache_info=None),
                }
            ),
            section_plugins=section_plugins,
        )

    def test_straight_forward_case(self) -> None:
        resolver = self.make_provider(
            section_plugins=dict((_section("section_one", "parsed_section_name", set()),))
        )

        resolved = resolver.resolve(ParsedSectionName("parsed_section_name"))
        assert resolved is not None
        assert resolved.parsed_data == 1
        assert resolved.section_name == SectionName("section_one")
        assert resolver.resolve(ParsedSectionName("no_such_section")) is None

    def test_superseder_is_present(self) -> None:
        resolver = self.make_provider(
            section_plugins=dict(
                (
                    _section("section_one", "parsed_section_one", set()),
                    _section("section_two", "parsed_section_two", {"section_one"}),
                )
            )
        )

        assert resolver.resolve(ParsedSectionName("parsed_section_one")) is None

    def test_superseder_with_same_name(self) -> None:
        resolver = self.make_provider(
            section_plugins=dict(
                (
                    _section("section_one", "parsed_section", set()),
                    _section("section_two", "parsed_section", {"section_one"}),
                )
            )
        )

        resolved = resolver.resolve(ParsedSectionName("parsed_section"))
        assert resolved is not None
        assert resolved.parsed_data == 2
        assert resolved.section_name == SectionName("section_two")

    def test_superseder_has_no_data(self) -> None:
        resolver = self.make_provider(
            section_plugins=dict(
                (
                    _section("section_one", "parsed_section_one", set()),
                    _section("section_iix", "parsed_section_iix", {"section_one"}),
                )
            )
        )

        resolved = resolver.resolve(ParsedSectionName("parsed_section_one"))
        assert resolved is not None
        assert resolved.parsed_data == 1
        assert resolved.section_name == SectionName("section_one")

    def test_iteration(self) -> None:
        host_key = HostKey(HostName("host"), SourceType.HOST)
        sections = dict(
            (
                _section("section_one", "parsed_section_one", set()),
                _section("section_two", "parsed_section_two", set()),
                _section("section_thr", "parsed_section_thr", {"section_two"}),
                _section("section_fou", "parsed_section_fou", {"section_one"}),
            )
        )
        providers = {host_key: self.make_provider(sections)}

        assert all_parsing_results(host_key, providers) == [
            ResolvedResult(section_name=SectionName("section_one"), parsed_data=1, cache_info=None),
            ResolvedResult(section_name=SectionName("section_thr"), parsed_data=3, cache_info=None),
        ]


def _test_section(
    *,
    section_name: str,
    parsed_section_name: str,
    parse_function: Callable,
    supersedes: Iterable[str],
) -> tuple[SectionName, SectionPlugin]:
    return SectionName(section_name), SectionPlugin(
        supersedes={SectionName(n) for n in supersedes},
        parse_function=parse_function,
        parsed_section_name=ParsedSectionName(parsed_section_name),
    )


SECTION_ONE = _test_section(
    section_name="one",
    parsed_section_name="parsed",
    parse_function=lambda x: {"parsed_by": "one", "node": x[0][0]},
    supersedes=(),
)

SECTION_TWO = _test_section(
    section_name="two",
    parsed_section_name="parsed",
    parse_function=lambda x: {"parsed_by": "two", "node": x[0][0]},
    supersedes={"one"},
)

SECTION_THREE = _test_section(
    section_name="three",
    parsed_section_name="parsed2",
    parse_function=lambda x: {"parsed_by": "three", "node": x[0][0]},
    supersedes=(),
)

SECTION_FOUR = _test_section(
    section_name="four",
    parsed_section_name="parsed_four",
    parse_function=lambda x: {"parsed_by": "four", "node": x[0][0]},
    supersedes={"one"},
)

NODE_1: Sequence[AgentRawDataSectionElem] = [
    ["node1", "data 1"],
    ["node1", "data 2"],
]

NODE_2: Sequence[AgentRawDataSectionElem] = [
    ["node2", "data 1"],
    ["node2", "data 2"],
]


def make_parser() -> SectionsParser:
    return SectionsParser(
        HostSections[AgentRawDataSection](
            sections={
                SectionName("one"): NODE_1,
                SectionName("four"): NODE_1,
            }
        ),
        host_name=HostName("some-host"),
        error_handling=lambda *args, **kw: "error",
    )


def test_parse_sections_unsuperseded() -> None:
    assert (
        ParsedSectionsResolver(
            make_parser(),
            section_plugins=dict((SECTION_ONE, SECTION_THREE)),
        ).resolve(ParsedSectionName("parsed"))
        is not None
    )


def test_parse_sections_superseded() -> None:
    assert (
        ParsedSectionsResolver(
            make_parser(), section_plugins=dict((SECTION_ONE, SECTION_THREE, SECTION_FOUR))
        ).resolve(ParsedSectionName("parsed"))
        is None
    )


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
        section_name = SectionName("one")

        def parse_function(*args: object, **kw: object) -> object:
            return next(counter)

        _ = sections_parser.parse(section_name, parse_function)
        parsing_result = sections_parser.parse(section_name, parse_function)

        assert parsing_result is not None
        assert parsing_result.data == 1

    @staticmethod
    @pytest.mark.usefixtures("disable_debug")
    def test_parsing_errors(
        sections_parser: SectionsParser[AgentRawDataSectionElem],
    ) -> None:
        section_name = SectionName("one")

        assert sections_parser.parse(section_name, lambda *args, **kw: 1 / 0) is None
        assert len(sections_parser.parsing_errors) == 1
        assert sections_parser.parsing_errors == ["error"]

    @staticmethod
    def test_parse(sections_parser: SectionsParser[AgentRawDataSectionElem]) -> None:
        parsed_data = object()
        section_name = SectionName("one")

        parsing_result = sections_parser.parse(section_name, lambda *args, **kw: parsed_data)

        assert parsing_result is not None
        assert parsing_result.data is parsed_data
        assert parsing_result.cache_info is None

    @staticmethod
    def test_disable(sections_parser: SectionsParser[AgentRawDataSectionElem]) -> None:
        section_name = SectionName("one")

        sections_parser.disable([section_name])

        assert sections_parser.parse(section_name, lambda *args, **kw: 42) is None

    @staticmethod
    def test_parse_missing_section(
        sections_parser: SectionsParser[AgentRawDataSectionElem],
    ) -> None:
        section_name = SectionName("missing_section")

        assert sections_parser.parse(section_name, lambda *args, **kw: 42) is None

    @staticmethod
    def test_parse_section_returns_none(
        sections_parser: SectionsParser[AgentRawDataSectionElem],
    ) -> None:
        section_name = SectionName("one")

        assert sections_parser.parse(section_name, lambda *args, **kw: None) is None
