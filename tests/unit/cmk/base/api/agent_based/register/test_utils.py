#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=invalid-name  # make them longer!

from typing import NamedTuple, List, Set

#import pytest  # type: ignore[import]

from cmk.utils.type_defs import ParsedSectionName, SectionName
from cmk.base.api.agent_based.register import utils


class _FakeSectionPlugin(NamedTuple):
    name: SectionName
    parsed_section_name: ParsedSectionName
    supersedes: Set[SectionName]


def _create_creator(name: str, parsed_name: str, supersedes: List[str]):
    return SectionName(name), _FakeSectionPlugin(SectionName(name), ParsedSectionName(parsed_name),
                                                 {SectionName(n) for n in supersedes})


def test_rank_sections_by_supersedes_no_matching_sections():

    fallback = _create_creator("desired", "desired", [])

    assert utils.rank_sections_by_supersedes(
        [
            _create_creator("foo", "foo", []),
        ],
        {ParsedSectionName("desired")},
    ) == []

    assert utils.rank_sections_by_supersedes(
        [
            fallback,
            _create_creator("foo", "foo", []),
        ],
        {ParsedSectionName("desired")},
    ) == [fallback[1]]

    assert utils.rank_sections_by_supersedes(
        [
            fallback,
            _create_creator("foo", "foo", []),
            _create_creator("desired", "bar", []),  # will create "bar", not "desired"!
        ],
        {ParsedSectionName("desired")},
    ) == [fallback[1]]


def test_rank_section_by_supersedes_with_supersedings():

    available = [
        _create_creator("ding", "dong", ["moo"]),  # filter this out!
        _create_creator("foo1", "desired", ["ding", "moo", "foo3"]),  # one of three is relevant
        _create_creator("foo2", "desired", ["zfoo4", "afoo5"]),  # only two, but all relevant
        _create_creator("foo3", "desired", ["ding"]),
        _create_creator("zfoo4", "desired", []),
        _create_creator("afoo5", "desired", []),
    ]
    assert utils.rank_sections_by_supersedes(
        available,
        {ParsedSectionName("desired")},
    ) == [available[i][1] for i in (2, 1, 5, 3, 4)]
