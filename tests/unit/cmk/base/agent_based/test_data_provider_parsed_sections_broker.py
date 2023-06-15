#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Sequence

from pytest import MonkeyPatch

from cmk.utils.type_defs import HostName, SectionName

from cmk.checkengine import SectionPlugin
from cmk.checkengine.host_sections import HostSections
from cmk.checkengine.sectionparser import ParsedSectionName, ParsedSectionsResolver, SectionsParser
from cmk.checkengine.type_defs import AgentRawDataSection


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

NODE_1: Sequence[AgentRawDataSection] = [
    ["node1", "data 1"],
    ["node1", "data 2"],
]

NODE_2: Sequence[AgentRawDataSection] = [
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
    )


def test_parse_sections_unsuperseded(monkeypatch: MonkeyPatch) -> None:
    assert (
        ParsedSectionsResolver(
            make_parser(),
            section_plugins=dict((SECTION_ONE, SECTION_THREE)),
        ).resolve(ParsedSectionName("parsed"))
        is not None
    )


def test_parse_sections_superseded(monkeypatch: MonkeyPatch) -> None:
    assert (
        ParsedSectionsResolver(
            make_parser(), section_plugins=dict((SECTION_ONE, SECTION_THREE, SECTION_FOUR))
        ).resolve(ParsedSectionName("parsed"))
        is None
    )
