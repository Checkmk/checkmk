#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from collections.abc import Iterable, Mapping

from cmk.utils.type_defs import HostName, ParsedSectionName, SectionName

from cmk.checkers import HostKey, SourceType

from cmk.base.agent_based.data_provider import _ParsingResult as ParsingResult
from cmk.base.agent_based.data_provider import ParsedSectionsResolver, ResolvedResult
from cmk.base.agent_based.discovery._host_labels import _all_parsing_results as all_parsing_results
from cmk.base.api.agent_based.register.section_plugins import trivial_section_factory
from cmk.base.api.agent_based.type_defs import SectionPlugin

# import pytest


def _section(name: str, parsed_section_name: str, supersedes: set[str]) -> SectionPlugin:
    section = trivial_section_factory(SectionName(name))
    return section._replace(
        parsed_section_name=ParsedSectionName(parsed_section_name),
        supersedes={SectionName(n) for n in supersedes},
    )


class _FakeParser(dict):
    def parse(self, section_name: SectionName, *args: object):  # type:ignore[no-untyped-def]
        return self.get(str(section_name))

    def disable(self, names: Iterable[SectionName]) -> None:
        for name in names:
            _ = self.pop(str(name), None)


class TestParsedSectionsResolver:
    @staticmethod
    def make_provider(
        section_plugins: Mapping[SectionName, SectionPlugin],
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
            section_plugins={
                SectionName("section_one"): _section("section_one", "parsed_section_name", set()),
            }
        )

        resolved = resolver.resolve(ParsedSectionName("parsed_section_name"))
        assert resolved is not None
        assert resolved.parsed_data == 1
        assert resolved.section_name == SectionName("section_one")
        assert resolver.resolve(ParsedSectionName("no_such_section")) is None

    def test_superseder_is_present(self) -> None:
        resolver = self.make_provider(
            section_plugins={
                SectionName("section_one"): _section("section_one", "parsed_section_one", set()),
                SectionName("section_two"): _section(
                    "section_two", "parsed_section_two", {"section_one"}
                ),
            }
        )

        assert resolver.resolve(ParsedSectionName("parsed_section_one")) is None

    def test_superseder_with_same_name(self) -> None:
        resolver = self.make_provider(
            section_plugins={
                SectionName("section_one"): _section("section_one", "parsed_section", set()),
                SectionName("section_two"): _section(
                    "section_two", "parsed_section", {"section_one"}
                ),
            }
        )

        resolved = resolver.resolve(ParsedSectionName("parsed_section"))
        assert resolved is not None
        assert resolved.parsed_data == 2
        assert resolved.section_name == SectionName("section_two")

    def test_superseder_has_no_data(self) -> None:
        resolver = self.make_provider(
            section_plugins={
                SectionName("section_one"): _section("section_one", "parsed_section_one", set()),
                SectionName("section_iix"): _section(
                    "section_iix", "parsed_section_iix", {"section_one"}
                ),
            }
        )

        resolved = resolver.resolve(ParsedSectionName("parsed_section_one"))
        assert resolved is not None
        assert resolved.parsed_data == 1
        assert resolved.section_name == SectionName("section_one")

    def test_iteration(self) -> None:
        host_key = HostKey(HostName("host"), SourceType.HOST)
        sections = {
            SectionName("section_one"): _section("section_one", "parsed_section_one", set()),
            SectionName("section_two"): _section("section_two", "parsed_section_two", set()),
            SectionName("section_thr"): _section(
                "section_thr", "parsed_section_thr", {"section_two"}
            ),
            SectionName("section_fou"): _section(
                "section_fou", "parsed_section_fou", {"section_one"}
            ),
        }
        providers = {host_key: self.make_provider(sections)}  # type: ignore[dict-item]

        assert all_parsing_results(host_key, providers) == [  # type: ignore[arg-type]
            ResolvedResult(section_name=SectionName("section_one"), parsed_data=1, cache_info=None),
            ResolvedResult(section_name=SectionName("section_thr"), parsed_data=3, cache_info=None),
        ]
