#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Any, Callable, Dict, Iterable, Sequence

import pytest

from cmk.utils.check_utils import ActiveCheckResult
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
from cmk.base.agent_based.utils import (
    check_parsing_errors,
    get_section_cluster_kwargs,
    get_section_kwargs,
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
    "required_sections,expected_result",
    [
        (["nonexistent"], {}),
        (["parsed"], {"section": {"parsed_by": "two", "node": "node1"}}),
        (
            ["parsed", "nonexistent"],
            {"section_parsed": {"parsed_by": "two", "node": "node1"}, "section_nonexistent": None},
        ),
        (
            ["parsed", "parsed2"],
            {
                "section_parsed": {"parsed_by": "two", "node": "node1"},
                "section_parsed2": {"parsed_by": "three", "node": "node1"},
            },
        ),
    ],
)
def test_get_section_kwargs(
    required_sections: Sequence[str], expected_result: Dict[str, Dict[str, str]]
) -> None:

    node_sections = HostSections[AgentRawDataSection](
        sections={
            SectionName("one"): NODE_1,
            SectionName("two"): NODE_1,
            SectionName("three"): NODE_1,
        }
    )

    host_key = HostKey(HostName("node1"), HostAddress("127.0.0.1"), SourceType.HOST)

    parsed_sections_broker = ParsedSectionsBroker(
        {
            host_key: (
                ParsedSectionsResolver(
                    section_plugins=[SECTION_ONE, SECTION_TWO, SECTION_THREE, SECTION_FOUR]
                ),
                SectionsParser(host_sections=node_sections, host_name=host_key.hostname),
            ),
        }
    )

    kwargs = get_section_kwargs(
        parsed_sections_broker,
        host_key,
        [ParsedSectionName(n) for n in required_sections],
    )

    assert expected_result == kwargs


@pytest.mark.parametrize(
    "required_sections,expected_result",
    [
        (["nonexistent"], {}),
        (
            ["parsed"],
            {
                "section": {
                    "node1": {"parsed_by": "two", "node": "node1"},
                    "node2": {"parsed_by": "two", "node": "node2"},
                }
            },
        ),
        (
            ["parsed", "nonexistent"],
            {
                "section_parsed": {
                    "node1": {"parsed_by": "two", "node": "node1"},
                    "node2": {"parsed_by": "two", "node": "node2"},
                },
                "section_nonexistent": {"node1": None, "node2": None},
            },
        ),
        (
            ["parsed", "parsed2"],
            {
                "section_parsed": {
                    "node1": {"parsed_by": "two", "node": "node1"},
                    "node2": {"parsed_by": "two", "node": "node2"},
                },
                "section_parsed2": {
                    "node1": {"parsed_by": "three", "node": "node1"},
                    "node2": {"parsed_by": "three", "node": "node2"},
                },
            },
        ),
    ],
)
def test_get_section_cluster_kwargs(
    required_sections: Sequence[str], expected_result: Dict[str, Any]
) -> None:

    node1_sections = HostSections[AgentRawDataSection](
        sections={
            SectionName("one"): NODE_1,
            SectionName("two"): NODE_1,
            SectionName("three"): NODE_1,
        }
    )

    node2_sections = HostSections[AgentRawDataSection](
        sections={
            SectionName("two"): NODE_2,
            SectionName("three"): NODE_2,
        }
    )

    parsed_sections_broker = ParsedSectionsBroker(
        {
            HostKey(HostName("node1"), HostAddress("127.0.0.1"), SourceType.HOST): (
                ParsedSectionsResolver(
                    section_plugins=[SECTION_ONE, SECTION_TWO, SECTION_THREE, SECTION_FOUR],
                ),
                SectionsParser(host_sections=node1_sections, host_name=HostName("node1")),
            ),
            HostKey(HostName("node2"), HostAddress("127.0.0.1"), SourceType.HOST): (
                ParsedSectionsResolver(
                    section_plugins=[SECTION_ONE, SECTION_TWO, SECTION_THREE, SECTION_FOUR],
                ),
                SectionsParser(host_sections=node2_sections, host_name=HostName("node2")),
            ),
        }
    )

    kwargs = get_section_cluster_kwargs(
        parsed_sections_broker,
        [
            HostKey(HostName("node1"), HostAddress("127.0.0.1"), SourceType.HOST),
            HostKey(HostName("node2"), HostAddress("127.0.0.1"), SourceType.HOST),
        ],
        [ParsedSectionName(n) for n in required_sections],
    )

    assert expected_result == kwargs


def test_check_parsing_errors_no_errors() -> None:
    assert not check_parsing_errors(())


def test_check_parsing_errors_are_ok() -> None:
    assert check_parsing_errors(
        ("error - message",),
        error_state=0,
    ) == [ActiveCheckResult(0, "error", ("error - message",))]


def test_check_parsing_errors_with_errors_() -> None:
    assert check_parsing_errors(("error - message",)) == [
        ActiveCheckResult(1, "error", ("error - message",))
    ]
    assert check_parsing_errors(
        ("error - message",),
        error_state=2,
    ) == [ActiveCheckResult(2, "error", ("error - message",))]
