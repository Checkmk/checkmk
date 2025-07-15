#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import copy
import itertools
import logging
import time
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.sectionname import SectionName
from cmk.utils.translations import TranslationOptions

from cmk.snmplib import SNMPRawData

from cmk.checkengine.parser import (
    AgentParser,
    AgentRawDataSectionElem,
    NO_SELECTION,
    SectionStore,
    SNMPParser,
)
from cmk.checkengine.parser._agent import ParserState
from cmk.checkengine.parser._markers import PiggybackMarker, SectionMarker

StringTable = list[list[str]]


class TestAgentParser:
    @pytest.fixture
    def hostname(self) -> HostName:
        return HostName("testhost")

    @pytest.fixture
    def logger(self):
        return logging.getLogger("test")

    @pytest.fixture
    def store_path(self, tmp_path):
        return tmp_path / "store"

    @pytest.fixture
    def store(self, store_path, logger):
        return SectionStore[Sequence[AgentRawDataSectionElem]](store_path, logger=logger)

    @pytest.fixture
    def parser(
        self,
        hostname: HostName,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        logger: logging.Logger,
    ) -> AgentParser:
        return AgentParser(
            hostname,
            store,
            host_check_interval=0,
            keep_outdated=True,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

    def test_missing_host_header(
        self, parser: AgentParser, store: SectionStore[Sequence[AgentRawDataSectionElem]]
    ) -> None:
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"hey!",
                    b"a header",
                    b"is missing",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert not store.load()

    def test_piggy_name_as_hostname_is_not_piggybacked(
        self,
        parser: AgentParser,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        hostname: HostName,
    ) -> None:
        host_name_bytes = str(hostname).encode("ascii")
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<%s>>>>" % host_name_bytes,
                    b"line0",
                    b"line1",
                    b"line2",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert not store.load()

    def test_no_section_header_after_piggyback(
        self, parser: AgentParser, store: SectionStore[Sequence[AgentRawDataSectionElem]]
    ) -> None:
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<piggy>>>>",
                    b"line0",
                    b"line1",
                    b"line2",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {HostName("piggy"): []}
        assert not store.load()

    def test_raw_section_populates_sections(
        self, parser: AgentParser, store: SectionStore[Sequence[AgentRawDataSectionElem]]
    ) -> None:
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<a_section>>>",
                    b"first line",
                    b"second line",
                    b"<<<>>>",  # ignored
                    b"<<<another_section>>>",
                    b"first line",
                    b"second line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {
            SectionName("a_section"): [["first", "line"], ["second", "line"]],
            SectionName("another_section"): [["first", "line"], ["second", "line"]],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert not store.load()

    def test_partial_header_is_not_a_header(
        self, parser: AgentParser, store: SectionStore[Sequence[AgentRawDataSectionElem]]
    ) -> None:
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<a_section>>>",
                    b"<<< first line",
                    b">>> second line",
                    b"third line >>>",
                    b"forth line <<<",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("a_section"): [
                ["<<<", "first", "line"],
                [">>>", "second", "line"],
                ["third", "line", ">>>"],
                ["forth", "line", "<<<"],
            ]
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert not store.load()

    def test_merge_split_raw_sections(
        self, parser: AgentParser, store: SectionStore[Sequence[AgentRawDataSectionElem]]
    ) -> None:
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<a_section>>>",
                    b"first line",
                    b"second line",
                    b"<<<another_section>>>",
                    b"a line",
                    b"b line",
                    b"<<<a_section>>>",
                    b"third line",
                    b"forth line",
                    b"<<<another_section>>>",
                    b"c line",
                    b"d line",
                    b"<<<a_section:sep(124)>>>",
                    b"fifth|line",
                    b"sixth|line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("a_section"): [
                ["first", "line"],
                ["second", "line"],
                ["third", "line"],
                ["forth", "line"],
                ["fifth", "line"],
                ["sixth", "line"],
            ],
            SectionName("another_section"): [
                ["a", "line"],
                ["b", "line"],
                ["c", "line"],
                ["d", "line"],
            ],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert not store.load()

    def test_nameless_sections_are_skipped(
        self, parser: AgentParser, store: SectionStore[Sequence[AgentRawDataSectionElem]]
    ) -> None:
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<a_section>>>",
                    b"a first line",
                    b"a second line",
                    b"<<<:cached(10, 5)>>>",
                    b"ignored first line",
                    b"ignored second line",
                    b"<<<b_section>>>",
                    b"b first line",
                    b"b second line",
                    b"<<<>>>",
                    b"ignored third line",
                    b"ignored forth line",
                    b"<<<c_section>>>",
                    b"c first line",
                    b"c second line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("a_section"): [["a", "first", "line"], ["a", "second", "line"]],
            SectionName("b_section"): [["b", "first", "line"], ["b", "second", "line"]],
            SectionName("c_section"): [["c", "first", "line"], ["c", "second", "line"]],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert not store.load()

    def test_nameless_piggybacked_sections_are_skipped(
        self,
        parser: AgentParser,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "cache_piggybacked_data_for", 900)

        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<piggyback_header>>>>",
                    b"<<<a_section>>>",
                    b"a first line",
                    b"a second line",
                    b"<<<:cached(10, 5)>>>",
                    b"ignored first line",
                    b"ignored second line",
                    b"<<<>>>",
                    b"ignored third line",
                    b"ignored forth line",
                    b"<<<b_section>>>",
                    b"b first line",
                    b"b second line",
                    b"<<<>>>",
                    b"ignored fifth line",
                    b"ignored sixth line",
                )
            )
        )
        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggyback_header": [
                b"<<<a_section:cached(1000,900)>>>",
                b"a first line",
                b"a second line",
                b"<<<b_section:cached(1000,900)>>>",
                b"b first line",
                b"b second line",
            ]
        }
        assert not store.load()

    def test_unrecoverably_invalid_hosts_are_ignored(self, parser: AgentParser) -> None:
        # a too long name can't be a valid hostname -- not even after character replacements
        too_long = b"piggybackedhost" * 100
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<section1>>>",
                    b"one line",
                    b"<<<<%s>>>>" % too_long,  # <- invalid host name
                    b"<<<this_goes_nowhere>>>",
                    b"dead line",
                    b"<<<<>>>>",
                    b"<<<section2>>>",
                    b"a first line",
                    b"a second line",
                )
            )
        )
        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert set(ahs.sections) == {SectionName("section1"), SectionName("section2")}
        assert ahs.piggybacked_raw_data == {}

    def test_invalid_hosts_are_projected(
        self, parser: AgentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "cache_piggybacked_data_for", 900)
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<section1>>>",
                    b"one line",
                    b"<<<<Foo Bar>>>>",  # <- invalid host name
                    b"<<<this_is_found>>>",
                    b"some line",
                    b"<<<<>>>>",
                    b"<<<section2>>>",
                    b"a first line",
                    b"a second line",
                )
            )
        )
        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert set(ahs.sections) == {SectionName("section1"), SectionName("section2")}
        assert ahs.piggybacked_raw_data == {
            "Foo_Bar": [b"<<<this_is_found:cached(1000,900)>>>", b"some line"]
        }

    def test_closing_piggyback_out_of_piggyback_section_closes_section(
        self, parser: AgentParser, store: SectionStore[Sequence[AgentRawDataSectionElem]]
    ) -> None:
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<a_section>>>",
                    b"first line",
                    b"second line",
                    b"<<<<>>>>",  # noop
                    b"<<<<>>>>",  # noop
                    b"<<<another_section>>>",
                    b"a line",
                    b"b line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("a_section"): [
                ["first", "line"],
                ["second", "line"],
            ],
            SectionName("another_section"): [
                ["a", "line"],
                ["b", "line"],
            ],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert not store.load()

    def test_piggyback_populates_piggyback_raw_data(
        self,
        parser: AgentParser,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "cache_piggybacked_data_for", 900)

        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<piggyback_header>>>>",
                    b"<<<section>>>",
                    b"first line",
                    b"second line",
                    b"<<<<>>>>",  # <- omitting this line makes no difference
                    b"<<<<piggyback_other>>>>",
                    b"<<<other_section>>>",
                    b"first line",
                    b"second line",
                    b"<<<other_other_section>>>",
                    b"third line",
                    b"forth line",
                    b"<<<<>>>>",
                    b"<<<</b_l-u/>>>>",
                    b"<<<section>>>",
                    b"first line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggyback_header": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
                b"second line",
            ],
            "piggyback_other": [
                b"<<<other_section:cached(1000,900)>>>",
                b"first line",
                b"second line",
                b"<<<other_other_section:cached(1000,900)>>>",
                b"third line",
                b"forth line",
            ],
            "_b_l-u_": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
            ],
        }
        assert not store.load()

    def test_merge_split_piggyback_sections(
        self,
        parser: AgentParser,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "cache_piggybacked_data_for", 900)

        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<piggy>>>>",
                    b"<<<a_section>>>",
                    b"first line",
                    b"second line",
                    b"<<<another_section>>>",
                    b"a line",
                    b"b line",
                    b"<<<<>>>>",
                    b"<<<<piggy>>>>",
                    b"<<<a_section>>>",
                    b"third line",
                    b"forth line",
                    b"<<<another_section>>>",
                    b"c line",
                    b"d line",
                    b"<<<<>>>>",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggy": [
                b"<<<a_section:cached(1000,900)>>>",
                b"first line",
                b"second line",
                b"<<<another_section:cached(1000,900)>>>",
                b"a line",
                b"b line",
                b"<<<a_section:cached(1000,900)>>>",
                b"third line",
                b"forth line",
                b"<<<another_section:cached(1000,900)>>>",
                b"c line",
                b"d line",
            ],
        }
        assert not store.load()

    def test_persist_option_populates_cache_info(
        self,
        parser: AgentParser,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<section:persist(%i)>>>" % (1000 + 50),
                    b"first line",
                    b"second line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {SectionName("section"): [["first", "line"], ["second", "line"]]}
        assert ahs.cache_info == {SectionName("section"): (1000, 50)}
        assert ahs.piggybacked_raw_data == {}
        assert store.load() == {
            SectionName("section"): (1000, 1050, [["first", "line"], ["second", "line"]]),
        }

    def test_persist_option_and_persisted_sections(
        self,
        parser: AgentParser,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(
            SectionStore,
            "load",
            lambda self: {
                SectionName("persisted"): (42, 69, [["content"]]),
            },
        )
        # Patch IO:
        monkeypatch.setattr(SectionStore, "store", lambda self, sections: None)

        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<section:persist(%i)>>>" % (1000 + 50),
                    b"first line",
                    b"second line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {
            SectionName("section"): [["first", "line"], ["second", "line"]],
            SectionName("persisted"): [["content"]],
        }
        assert ahs.cache_info == {
            SectionName("section"): (1000, 50),
            SectionName("persisted"): (42, 27),
        }
        assert ahs.piggybacked_raw_data == {}
        assert store.load() == {
            SectionName("persisted"): (42, 69, [["content"]]),
        }

    def test_section_filtering_and_merging_host(
        self,
        parser: AgentParser,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<deselected:persist(1000)>>>",
                    b"1st line",
                    b"2nd line",
                    b"<<<selected:persist(1000)>>>",
                    b"3rd line",
                    b"4th line",
                    b"<<<deselected:persist(1000)>>>",
                    b"5th line",
                    b"6th line",
                    b"<<<selected:persist(1000)>>>",
                    b"7th line",
                    b"8th line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=frozenset({SectionName("selected")}))

        assert ahs.sections == {
            SectionName("selected"): [
                ["3rd", "line"],
                ["4th", "line"],
                ["7th", "line"],
                ["8th", "line"],
            ],
        }
        assert ahs.cache_info == {SectionName("selected"): (1000, 0)}
        assert ahs.piggybacked_raw_data == {}
        assert store.load() == {
            SectionName("selected"): (
                1000,
                1000,
                [
                    ["3rd", "line"],
                    ["4th", "line"],
                    ["7th", "line"],
                    ["8th", "line"],
                ],
            )
        }

    def test_section_filtering_and_merging_piggyback(
        self,
        parser: AgentParser,
        store: SectionStore[Sequence[AgentRawDataSectionElem]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<piggyback_header>>>>",
                    b"<<<deselected>>>",
                    b"1st line",
                    b"2nd line",
                    b"<<<selected>>>",
                    b"3rd line",
                    b"4th line",
                    b"<<<<>>>>",
                    b"<<<deselected>>>",
                    b"5th line",
                    b"6th line",
                    b"<<<selected>>>",
                    b"7th line",
                    b"8th line",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=frozenset({SectionName("selected")}))

        assert ahs.sections == {
            SectionName("selected"): [["7th", "line"], ["8th", "line"]],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggyback_header": [
                b"<<<selected:cached(1000,0)>>>",
                b"3rd line",
                b"4th line",
            ]
        }
        assert not store.load()

    def test_section_lines_are_correctly_ordered_with_different_separators(
        self, parser: AgentParser, store: SectionStore[Sequence[AgentRawDataSectionElem]]
    ) -> None:
        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<section:sep(124)>>>",
                    b"a|1",
                    b"<<<section:sep(44)>>>",
                    b"b,2",
                    b"<<<section:sep(124)>>>",
                    b"c|3",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("section"): [
                ["a", "1"],
                ["b", "2"],
                ["c", "3"],
            ],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert not store.load()

    def test_section_lines_are_correctly_ordered_with_different_separators_and_piggyback(
        self, parser, store, monkeypatch
    ):
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "cache_piggybacked_data_for", 900)

        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<piggy>>>>",
                    b"<<<section:sep(124)>>>",
                    b"a|1",
                    b"<<<section:sep(44)>>>",
                    b"b,2",
                    b"<<<section:sep(124)>>>",
                    b"c|3",
                )
            )
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggy": [
                b"<<<section:cached(1000,900):sep(124)>>>",
                b"a|1",
                b"<<<section:cached(1000,900):sep(44)>>>",
                b"b,2",
                b"<<<section:cached(1000,900):sep(124)>>>",
                b"c|3",
            ],
        }
        assert store.load() == {}


class ParserStateAdapter(ParserState):
    def __init__(self, *, translation: TranslationOptions | None = None):
        super().__init__(
            HostName("foo"),
            sections=[],
            piggyback_sections={},
            translation={} if translation is None else translation,
            encoding_fallback="utf-8",
            logger=logging.getLogger(),
        )

    def do_action(self, line: bytes) -> ParserState:
        raise AssertionError("unexpected data line")

    def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
        raise AssertionError("unexpected piggyback header")

    def on_piggyback_footer(self) -> ParserState:
        raise AssertionError("unexpected piggyback footer")

    def on_section_header(self, section_header: SectionMarker) -> ParserState:
        raise AssertionError("unexpected section header")

    def on_section_footer(self) -> ParserState:
        raise AssertionError("unexpected section footer")


class TestSectionMarker:
    @pytest.mark.parametrize(
        "line",
        [
            b"<<<section>>>",
            b"<<<section:cached(1,2):encoding(ascii):nostrip():persist(42):sep(124)>>>",
        ],
    )
    def test_stringify(self, line: bytes) -> None:
        parsed: SectionMarker | None = None

        class ExpectSectionHeader(ParserStateAdapter):
            def on_section_header(self, section_header: SectionMarker) -> ParserState:
                nonlocal parsed
                parsed = section_header
                return self

        ExpectSectionHeader()(line)
        parsed_line = parsed
        ExpectSectionHeader()(str(parsed).encode("ascii"))
        assert parsed_line == parsed
        assert str(parsed_line) == str(parsed)

    @pytest.mark.parametrize(
        "line, expected",
        [
            (  # defaults
                b"<<<norris>>>",
                SectionMarker(
                    name=SectionName("norris"),
                    cached=None,
                    encoding="utf-8",
                    nostrip=False,
                    persist=None,
                    separator=None,
                ),
            ),
            (
                b"<<<norris:encoding(chuck)>>>",
                SectionMarker(
                    name=SectionName("norris"),
                    cached=None,
                    encoding="chuck",
                    nostrip=False,
                    persist=None,
                    separator=None,
                ),
            ),
            (
                b"<<<my_section:sep(0):cached(23,42)>>>",
                SectionMarker(
                    name=SectionName("my_section"),
                    cached=(23, 42),
                    encoding="utf-8",
                    nostrip=False,
                    persist=None,
                    separator="\x00",
                ),
            ),
            (
                b"<<<name:cached(1,2):encoding(ascii):nostrip():persist(42):sep(124)>>>",
                SectionMarker(
                    name=SectionName("name"),
                    cached=(1, 2),
                    encoding="ascii",
                    nostrip=True,
                    persist=42,
                    separator="|",
                ),
            ),
            (  # option without parentheses gets ignored
                b"<<<norris:encoding:encoding(dong)>>>",
                SectionMarker(
                    name=SectionName("norris"),
                    cached=None,
                    encoding="dong",
                    nostrip=False,
                    persist=None,
                    separator=None,
                ),
            ),
            (  # unknown option gets ignored
                b"<<<norris:hurz(42):encoding(blah)>>>",
                SectionMarker(
                    name=SectionName("norris"),
                    cached=None,
                    encoding="blah",
                    nostrip=False,
                    persist=None,
                    separator=None,
                ),
            ),
            (b"<<<my.section:sep(0):cached(23,42)>>>", None),  # invalid section name
            (b"<<< >>>", None),  # invalid section name
        ],
    )
    def test_options_from_headerline(self, line: bytes, expected: SectionMarker | None) -> None:
        class ExpectSectionHeader(ParserStateAdapter):
            def on_section_header(self, section_header: SectionMarker) -> ParserState:
                assert section_header == expected
                return self

        try:
            ExpectSectionHeader()(line)
        except ValueError:
            assert expected is None


class TestSNMPParser:
    @pytest.fixture
    def hostname(self):
        return "hostname"

    @pytest.fixture
    def parser(self, hostname):
        return SNMPParser(
            hostname,
            SectionStore(
                "/tmp/store",
                logger=logging.Logger("test"),
            ),
            persist_periods={},
            host_check_interval=60,
            keep_outdated=True,
            logger=logging.Logger("test"),
        )

    def test_empty_raw_data(self, parser: SNMPParser) -> None:
        raw_data: SNMPRawData = {}

        host_sections = parser.parse(raw_data, selection=NO_SELECTION)
        assert host_sections.sections == {}
        assert host_sections.cache_info == {}
        assert not host_sections.piggybacked_raw_data

    @pytest.fixture
    def sections(self):
        # See also the tests to HostSections.
        section_a = SectionName("section_a")
        content_a = [["first", "line"], ["second", "line"]]
        section_b = SectionName("section_b")
        content_b = [["third", "line"], ["forth", "line"]]
        return {section_a: content_a, section_b: content_b}

    def test_no_cache(self, parser: SNMPParser, sections: dict[SectionName, StringTable]) -> None:
        host_sections = parser.parse(sections, selection=NO_SELECTION)
        assert host_sections.sections == sections
        assert host_sections.cache_info == {}
        assert not host_sections.piggybacked_raw_data

    def test_with_persisted_sections(
        self,
        parser: SNMPParser,
        sections: dict[SectionName, StringTable],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "persist_periods", defaultdict(lambda: 33))
        monkeypatch.setattr(
            SectionStore,
            "load",
            lambda self: {
                SectionName("persisted"): (42, 69, [["content"]]),
            },
        )
        # Patch IO:
        monkeypatch.setattr(SectionStore, "store", lambda self, sections: None)

        raw_data = sections

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        all_sections = sections.copy()
        all_sections[SectionName("persisted")] = [["content"]]
        assert ahs.sections == all_sections
        assert ahs.cache_info == {SectionName("persisted"): (42, 27)}
        assert ahs.piggybacked_raw_data == {}


class MockStore(SectionStore):
    def __init__(self, path: str | Path, sections: object, *, logger: logging.Logger) -> None:
        super().__init__(path, logger=logger)
        self._sections = sections

    def store(self, sections):
        self._sections = copy.copy(sections)

    def load(self):
        return copy.copy(self._sections)


class TestAgentPersistentSectionHandling:
    @pytest.fixture
    def logger(self):
        return logging.getLogger("test")

    def test_update_with_empty_store_and_empty_raw_data(self, logger: logging.Logger) -> None:
        section_store = MockStore("/dev/null", {}, logger=logger)
        raw_data = AgentRawData(b"")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            host_check_interval=0,
            keep_outdated=True,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert not ahs.sections
        assert not ahs.cache_info
        assert not ahs.piggybacked_raw_data
        assert section_store.load() == {}

    def test_update_with_store_and_empty_raw_data(self, logger: logging.Logger) -> None:
        section_store = MockStore(
            "/dev/null",
            {SectionName("stored"): (0, 0, [])},
            logger=logger,
        )
        raw_data = AgentRawData(b"")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            host_check_interval=0,
            keep_outdated=True,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("stored"): []}
        assert ahs.cache_info == {SectionName("stored"): (0, 0)}
        assert not ahs.piggybacked_raw_data
        assert section_store.load() == {SectionName("stored"): (0, 0, [])}

    def test_update_with_empty_store_and_raw_data(self, logger: logging.Logger) -> None:
        raw_data = AgentRawData(b"<<<fresh>>>")
        section_store = MockStore("/dev/null", {}, logger=logger)
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            host_check_interval=0,
            keep_outdated=True,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("fresh"): []}
        assert not ahs.cache_info
        assert not ahs.piggybacked_raw_data
        assert section_store.load() == {}

    def test_update_with_store_and_non_persisting_raw_data(self, logger: logging.Logger) -> None:
        section_store = MockStore(
            "/dev/null",
            {SectionName("stored"): (0, 0, [])},
            logger=logger,
        )
        raw_data = AgentRawData(b"<<<fresh>>>")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            host_check_interval=0,
            keep_outdated=True,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("fresh"): [],
            SectionName("stored"): [],
        }
        assert ahs.cache_info == {SectionName("stored"): (0, 0)}
        assert not ahs.piggybacked_raw_data
        assert section_store.load() == {SectionName("stored"): (0, 0, [])}

    def test_update_with_store_and_persisting_raw_data(
        self, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        section_store = MockStore(
            "/dev/null",
            {SectionName("stored"): (0, 0, [["canned", "section"]])},
            logger=logger,
        )
        raw_data = AgentRawData(b"<<<fresh:persist(10)>>>\nhello section")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            host_check_interval=0,
            keep_outdated=True,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("fresh"): [["hello", "section"]],
            SectionName("stored"): [["canned", "section"]],
        }
        assert ahs.cache_info == {
            SectionName("stored"): (0, 0),
            SectionName("fresh"): (1000, -990),
        }
        assert not ahs.piggybacked_raw_data
        assert section_store.load() == {
            SectionName("stored"): (0, 0, [["canned", "section"]]),
            SectionName("fresh"): (1000, 10, [["hello", "section"]]),
        }

    def test_update_store_with_newest(self, logger: logging.Logger) -> None:
        section_store = MockStore(
            "/dev/null",
            {SectionName("section"): (0, 0, [["oldest"]])},
            logger=logger,
        )
        raw_data = AgentRawData(b"<<<section>>>\nnewest")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            host_check_interval=0,
            keep_outdated=True,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("section"): [["newest"]]}
        assert not ahs.cache_info
        assert not ahs.piggybacked_raw_data
        assert section_store.load() == {SectionName("section"): (0, 0, [["oldest"]])}

    def test_keep_outdated_false(
        self, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        raw_data = AgentRawData(b"<<<another_section>>>")
        section_store = MockStore(
            "/dev/null",
            {SectionName("section"): (500, 600, [])},
            logger=logger,
        )
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            host_check_interval=42,
            keep_outdated=False,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("another_section"): []}
        assert not ahs.cache_info
        assert not ahs.piggybacked_raw_data
        assert section_store.load() == {}

    def test_keep_outdated_true(
        self, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        raw_data = AgentRawData(b"<<<another_section>>>")
        section_store = MockStore(
            "/dev/null",
            {SectionName("section"): (500, 600, [])},
            logger=logger,
        )
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            host_check_interval=42,
            keep_outdated=True,
            translation=TranslationOptions(),
            encoding_fallback="ascii",
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("another_section"): [],
            SectionName("section"): [],
        }
        assert ahs.cache_info == {SectionName("section"): (500, 100)}
        assert not ahs.piggybacked_raw_data
        assert section_store.load() == {SectionName("section"): (500, 600, [])}


class TestSNMPPersistedSectionHandling:
    @pytest.fixture
    def logger(self):
        return logging.getLogger("test")

    def test_update_with_empty_store_and_persisted(self, logger: logging.Logger) -> None:
        section_store = MockStore("/dev/null", {}, logger=logger)
        raw_data: SNMPRawData = {}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            persist_periods={},
            host_check_interval=60,
            keep_outdated=True,
            logger=logger,
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_empty_persisted(self, logger: logging.Logger) -> None:
        section_store = MockStore(
            "/dev/null",
            {SectionName("stored"): (0, 0, [["old"]])},
            logger=logger,
        )
        raw_data: SNMPRawData = {}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            persist_periods={},
            host_check_interval=60,
            keep_outdated=True,
            logger=logger,
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("stored"): [["old"]]}
        assert shs.cache_info == {SectionName("stored"): (0, 0)}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {
            SectionName("stored"): (0, 0, [["old"]]),
        }

    def test_update_with_empty_store(self, logger: logging.Logger) -> None:
        section_store = MockStore("/dev/null", {}, logger=logger)
        raw_data: SNMPRawData = {SectionName("fresh"): [["new"]]}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            persist_periods={},
            host_check_interval=60,
            keep_outdated=True,
            logger=logger,
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("fresh"): [["new"]]}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_persisted_and_store(self, logger: logging.Logger) -> None:
        section_store = MockStore(
            "/dev/null",
            {SectionName("stored"): (0, 0, [["old"]])},
            logger=logger,
        )
        raw_data: SNMPRawData = {SectionName("fresh"): [["new"]]}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            persist_periods={},
            host_check_interval=60,
            keep_outdated=True,
            logger=logger,
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {
            SectionName("stored"): [["old"]],
            SectionName("fresh"): [["new"]],
        }
        assert shs.cache_info == {SectionName("stored"): (0, 0)}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {
            SectionName("stored"): (0, 0, [["old"]]),
        }

    def test_check_intervals_updates_persisted(
        self, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        section_store = MockStore(
            "/dev/null",
            {SectionName("section"): (0, 0, [["old"]])},
            logger=logger,
        )
        raw_data: SNMPRawData = {SectionName("section"): [["new"]]}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            persist_periods={SectionName("section"): 42},
            host_check_interval=60,
            keep_outdated=True,
            logger=logger,
        )
        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("section"): [["new"]]}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {SectionName("section"): (1000, 1042, [["new"]])}

    def test_keep_outdated_false(
        self, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        section_store = MockStore(
            "/dev/null",
            {SectionName("section"): (500, 600, [["old"]])},
            logger=logger,
        )
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            persist_periods={SectionName("section"): 42},
            host_check_interval=60,
            keep_outdated=False,
            logger=logger,
        )
        shs = parser.parse({}, selection=NO_SELECTION)
        assert shs.sections == {}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_keep_outdated_true(
        self, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        section_store = MockStore(
            "/dev/null",
            {SectionName("section"): (500, 600, [["old"]])},
            logger=logger,
        )
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            persist_periods={SectionName("section"): 42},
            host_check_interval=60,
            keep_outdated=True,
            logger=logger,
        )
        shs = parser.parse({}, selection=NO_SELECTION)
        assert shs.sections == {SectionName("section"): [["old"]]}
        assert shs.cache_info == {
            SectionName("section"): (500, 100),
        }
        assert shs.piggybacked_raw_data == {}
        assert not section_store.load() == {SectionName("section"): (1000, 1042, [["old"]])}

    def test_section_expired_during_checking(
        self, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        section_store = MockStore(
            "/dev/null",
            {SectionName("section"): (890, 990, [["old"]])},
            logger=logger,
        )
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            persist_periods={SectionName("section"): 100},
            host_check_interval=60,
            keep_outdated=False,
            logger=logger,
        )
        shs = parser.parse({}, selection=NO_SELECTION)
        assert shs.sections == {SectionName("section"): [["old"]]}
        assert shs.cache_info == {
            SectionName("section"): (890, 100),
        }
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {SectionName("section"): (890, 990, [["old"]])}


class TestMarkers:
    @pytest.mark.parametrize("line", [b"<<<x>>>", b"<<<x:cached(10, 5)>>>"])
    def test_section_header(self, line: bytes) -> None:
        class ExpectSectionHeader(ParserStateAdapter):
            def on_section_header(self, section_header: SectionMarker) -> ParserState:
                return self

        ExpectSectionHeader()(line)

    @pytest.mark.parametrize("line", [b"<<<>>>", b"<<<:cached(10, 5)>>>"])
    def test_section_footer(self, line: bytes) -> None:
        class ExpectSectionFooter(ParserStateAdapter):
            def on_section_footer(self) -> ParserState:
                return self

        ExpectSectionFooter()(line)

    def test_piggybacked_host_header(self) -> None:
        class ExpectPiggybackHeader(ParserStateAdapter):
            def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
                return self

        ExpectPiggybackHeader()(b"<<<<x>>>>")

    def test_piggybacked_host_translation_results_in_None(self) -> None:
        class ExpectPiggybackHeader(ParserStateAdapter):
            def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
                assert piggyback_header.hostname is None
                return self

        ExpectPiggybackHeader(
            translation=TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[],
                regex=[(".*(.*?)", r"\1")],
            )
        )(b"<<<<x>>>>")

    def test_piggybacked_host_footer(self) -> None:
        class ExpectPiggybackFooter(ParserStateAdapter):
            def on_piggyback_footer(self) -> ParserState:
                return self

        ExpectPiggybackFooter()(b"<<<<>>>>")
