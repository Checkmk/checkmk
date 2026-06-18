#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery._discover.host_labels import (
    _all_parsing_results as all_parsing_results,
)
from cmk.checkengine.helper_interface import HostKey, SourceType
from cmk.checkengine.plugins import ParsedSectionName, SectionName
from cmk.checkengine.sectionparser import (
    _ParsingResult as ParsingResult,
)
from cmk.checkengine.sectionparser import (
    ParsedSectionsResolver,
    ResolvedResult,
    SectionPlugin,
)


class _FakeParser(dict[str, object]):
    def parse(self, section_name: SectionName, *args: object) -> object:
        return self.get(str(section_name))

    def disable(self, names: Iterable[SectionName]) -> None:
        for name in names:
            _ = self.pop(str(name), None)


def _section(
    name: str, parsed_section_name: str, supersedes: set[str]
) -> tuple[SectionName, SectionPlugin]:
    return SectionName(name), SectionPlugin(
        supersedes={SectionName(n) for n in supersedes},
        parsed_section_name=ParsedSectionName(parsed_section_name),
        parse_function=lambda *args, **kw: object,
    )


def _make_provider(
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


def test_all_parsing_results() -> None:
    host_key = HostKey(HostName("host"), SourceType.HOST)
    sections = dict(
        (
            _section("section_one", "parsed_section_one", set()),
            _section("section_two", "parsed_section_two", set()),
            _section("section_thr", "parsed_section_thr", {"section_two"}),
            _section("section_fou", "parsed_section_fou", {"section_one"}),
        )
    )
    providers = {host_key: _make_provider(sections)}

    assert all_parsing_results(host_key, providers) == [
        ResolvedResult(section_name=SectionName("section_one"), parsed_data=1, cache_info=None),
        ResolvedResult(section_name=SectionName("section_thr"), parsed_data=3, cache_info=None),
    ]
