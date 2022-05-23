#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Callable, Iterable, Mapping, Sequence

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.utils.type_defs import (
    HostAddress,
    HostKey,
    HostName,
    ParsedSectionName,
    SectionName,
    SourceType,
)

from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.type_defs import AgentRawDataSection

import cmk.base.api.agent_based.register.section_plugins as section_plugins
from cmk.base.agent_based.data_provider import (
    ParsedSectionsBroker,
    ParsedSectionsResolver,
    SectionsParser,
)


def _test_section(
    *,
    section_name: str,
    parsed_section_name: str,
    parse_function: Callable,
    supersedes: Iterable[str],
) -> section_plugins.AgentSectionPlugin:
    return section_plugins.trivial_section_factory(SectionName(section_name))._replace(
        parsed_section_name=ParsedSectionName(parsed_section_name),
        parse_function=parse_function,
        supersedes={SectionName(n) for n in supersedes},
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


@pytest.mark.parametrize(
    "node_sections,expected_result",
    [
        (HostSections[AgentRawDataSection](sections={}), None),
        (
            HostSections[AgentRawDataSection](sections={SectionName("one"): NODE_1}),
            {"parsed_by": "one", "node": "node1"},
        ),
        (
            HostSections[AgentRawDataSection](sections={SectionName("two"): NODE_1}),
            {"parsed_by": "two", "node": "node1"},
        ),
        (
            HostSections[AgentRawDataSection](
                sections={
                    SectionName("one"): NODE_1,
                    SectionName("two"): NODE_1,
                }
            ),
            {
                "parsed_by": "two",
                "node": "node1",
            },
        ),
    ],
)
def test_get_parsed_section(
    node_sections: HostSections[AgentRawDataSection], expected_result: Mapping
) -> None:

    parsed_sections_broker = ParsedSectionsBroker(
        {
            HostKey(HostName("node1"), HostAddress("127.0.0.1"), SourceType.HOST): (
                ParsedSectionsResolver(
                    section_plugins=[SECTION_ONE, SECTION_TWO, SECTION_THREE, SECTION_FOUR],
                ),
                SectionsParser(host_sections=node_sections, host_name=HostName("node1")),
            ),
        }
    )

    content = parsed_sections_broker.get_parsed_section(
        HostKey(HostName("node1"), HostAddress("127.0.0.1"), SourceType.HOST),
        ParsedSectionName("parsed"),
    )

    assert expected_result == content


def _get_parser() -> SectionsParser:
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
            section_plugins=(SECTION_ONE, SECTION_THREE),
        ).resolve(_get_parser(), ParsedSectionName("parsed"))
        is not None
    )


def test_parse_sections_superseded(monkeypatch: MonkeyPatch) -> None:

    assert (
        ParsedSectionsResolver(
            section_plugins=(SECTION_ONE, SECTION_THREE, SECTION_FOUR),
        ).resolve(_get_parser(), ParsedSectionName("parsed"))
        is None
    )
