#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Iterable, Sequence, Set

#import pytest  # type: ignore[import]

from cmk.utils.type_defs import ParsedSectionName, SectionName

from cmk.base.agent_based.data_provider import (
    ParsedSectionsResolver,
    ParsingResult,
    ResolvedResult,
)
from cmk.base.api.agent_based.register.section_plugins import trivial_section_factory
from cmk.base.api.agent_based.type_defs import SectionPlugin


def _section(name: str, parsed_section_name: str, supersedes: Set[str]) -> SectionPlugin:
    section = trivial_section_factory(SectionName(name))
    return section._replace(
        parsed_section_name=ParsedSectionName(parsed_section_name),
        supersedes={SectionName(n) for n in supersedes},
    )


class _FakeParser(dict):
    def parse(self, section: SectionPlugin):
        return self.get(str(section.name))

    def disable(self, names: Iterable[SectionName]) -> None:
        for name in names:
            _ = self.pop(str(name), None)


class TestPArsedSectionsResolver:
    @staticmethod
    def make_resolver(section_plugins: Sequence[SectionPlugin]) -> ParsedSectionsResolver:
        return ParsedSectionsResolver(
            sections_parser=_FakeParser({  # type: ignore[arg-type]
                "section_one": ParsingResult(data=1, cache_info=None),
                "section_two": ParsingResult(data=2, cache_info=None),
                "section_thr": ParsingResult(data=3, cache_info=None),
            }),
            section_plugins=section_plugins,
        )

    def test_straight_forward_case(self):
        resolver = self.make_resolver(section_plugins=[
            _section("section_one", "parsed_section_name", set()),
        ])

        resolved = resolver.resolve(ParsedSectionName("parsed_section_name"))
        assert resolved
        parsed, section = resolved
        assert parsed and parsed.data == 1
        assert section and section.name == SectionName("section_one")
        assert resolver.resolve(ParsedSectionName("no_such_section")) is None

    def test_superseder_is_present(self):
        resolver = self.make_resolver(section_plugins=[
            _section("section_one", "parsed_section_one", set()),
            _section("section_two", "parsed_section_two", {"section_one"}),
        ])

        assert resolver.resolve(ParsedSectionName("parsed_section_one")) is None

    def test_superseder_with_same_name(self):
        resolver = self.make_resolver(section_plugins=[
            _section("section_one", "parsed_section", set()),
            _section("section_two", "parsed_section", {"section_one"}),
        ])

        resolved = resolver.resolve(ParsedSectionName("parsed_section"))
        assert resolved
        parsed, section = resolved
        assert parsed and parsed.data == 2
        assert section and section.name == SectionName("section_two")

    def test_superseder_has_no_data(self):
        resolver = self.make_resolver(section_plugins=[
            _section("section_one", "parsed_section_one", set()),
            _section("section_iix", "parsed_section_iix", {"section_one"}),
        ])

        resolved = resolver.resolve(ParsedSectionName("parsed_section_one"))
        assert resolved
        parsed, section = resolved
        assert parsed and parsed.data == 1
        assert section and section.name == SectionName("section_one")

    def test_iteration(self):
        sections = [
            _section("section_one", "parsed_section_one", set()),
            _section("section_two", "parsed_section_two", set()),
            _section("section_thr", "parsed_section_thr", {"section_two"}),
            _section("section_fou", "parsed_section_fou", {"section_one"}),
        ]
        resolver = self.make_resolver(section_plugins=sections)

        assert sorted(resolver, key=lambda r: r.section.name) == [
            ResolvedResult(
                parsed=ParsingResult(data=1, cache_info=None),
                section=sections[0],
            ),
            ResolvedResult(
                parsed=ParsingResult(data=3, cache_info=None),
                section=sections[2],
            ),
        ]
