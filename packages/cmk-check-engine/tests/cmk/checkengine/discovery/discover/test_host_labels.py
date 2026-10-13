#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Iterator, Mapping

from cmk.agent_based.v1 import HostLabel
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery import discover_host_labels, HostLabelPlugin
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
from cmk.ruleset_matcher.labels import HostLabel as DiscoveredHostLabel


class _FakeParser(dict[str, object]):
    def parse(self, section_name: SectionName, *_args: object) -> object:
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
        parse_function=lambda *_args, **_kw: object,
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


def _os_family_labels(section: object) -> Iterator[HostLabel]:  # noqa: ARG001
    yield HostLabel("cmk/os_family", "linux")


def test_discover_host_labels_prefers_plugin_labels_to_inventorized_ones() -> None:
    host_name = HostName("host")
    providers = {
        HostKey(host_name, SourceType.HOST): _make_provider(
            dict((_section("section_one", "parsed_section_one", set()),))
        )
    }

    assert discover_host_labels(
        host_name,
        {
            SectionName("section_one"): HostLabelPlugin(
                function=_os_family_labels, parameters=lambda _host_name: None
            )
        },
        providers=providers,
        on_error=OnError.RAISE,
        inventorized_host_labels={"cmk/os_family": "windows"},
    ) == [DiscoveredHostLabel("cmk/os_family", "linux", SectionName("section_one"))]
