#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import copy
import itertools
import logging
import time
from collections import defaultdict
from typing import Sequence

import pytest

import cmk.utils.debug
from cmk.utils.type_defs import AgentRawData, HostName, SectionName

from cmk.snmplib.type_defs import SNMPRawData, SNMPRawDataSection

from cmk.core_helpers.agent import AgentParser, PiggybackMarker, SectionMarker
from cmk.core_helpers.cache import PersistedSections, SectionStore
from cmk.core_helpers.snmp import SNMPParser
from cmk.core_helpers.type_defs import AgentRawDataSection, NO_SELECTION


@pytest.fixture(autouse=True)
def enable_debug_fixture():
    debug_mode = cmk.utils.debug.debug_mode
    cmk.utils.debug.enable()
    yield
    cmk.utils.debug.debug_mode = debug_mode


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
        return SectionStore[AgentRawDataSection](store_path, logger=logger)

    @pytest.fixture
    def parser(self, hostname: HostName, store, logger):
        return AgentParser(
            hostname,
            store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

    def test_missing_host_header(self, parser, store) -> None:
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
        assert store.load() == {}

    def test_piggy_name_as_hostname_is_not_piggybacked(
        self, parser, store, hostname: HostName
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
        assert store.load() == {}

    def test_no_section_header_after_piggyback(self, parser, store) -> None:
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
        assert store.load() == {}

    def test_raw_section_populates_sections(self, parser, store) -> None:
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
        assert store.load() == {}

    def test_merge_split_raw_sections(self, parser, store) -> None:
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
        assert store.load() == {}

    def test_nameless_sections_are_skipped(self, parser, store) -> None:
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
        assert store.load() == {}

    def test_nameless_piggybacked_sections_are_skipped(self, parser, store, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "cache_piggybacked_data_for", 900)

        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<piggyback header>>>>",
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
        assert store.load() == {}

    def test_closing_piggyback_out_of_piggyback_section_closes_section(self, parser, store) -> None:
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
        assert store.load() == {}

    def test_piggyback_populates_piggyback_raw_data(self, parser, store, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "cache_piggybacked_data_for", 900)

        raw_data = AgentRawData(
            b"\n".join(
                (
                    b"<<<<piggyback header>>>>",  # <- space is OK
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
                    b"<<<<../b:l*a../>>>>",
                    b"<<<section>>>",
                    b"first line",
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
            ".._b_l_a.._": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
            ],
            "_b_l-u_": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
            ],
        }
        assert store.load() == {}

    def test_merge_split_piggyback_sections(self, parser, store, monkeypatch) -> None:
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
        assert store.load() == {}

    def test_persist_option_populates_cache_info(self, parser, store, mocker, monkeypatch) -> None:
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
        assert store.load() == PersistedSections[AgentRawDataSection](
            {
                SectionName("section"): (1000, 1050, [["first", "line"], ["second", "line"]]),
            }
        )

    def test_persist_option_and_persisted_sections(
        self, parser, store, mocker, monkeypatch
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(
            SectionStore,
            "load",
            lambda self: PersistedSections[AgentRawDataSection](
                {
                    SectionName("persisted"): (42, 69, [["content"]]),
                }
            ),
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
        assert store.load() == PersistedSections[AgentRawDataSection](
            {
                SectionName("persisted"): (42, 69, [["content"]]),
            }
        )

    def test_section_filtering_and_merging_host(self, parser, store, monkeypatch) -> None:
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

        ahs = parser.parse(raw_data, selection={SectionName("selected")})

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
        assert store.load() == PersistedSections[AgentRawDataSection](
            {
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
        )

    def test_section_filtering_and_merging_piggyback(self, parser, store, monkeypatch) -> None:
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

        ahs = parser.parse(raw_data, selection={SectionName("selected")})

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
        assert store.load() == {}

    def test_section_lines_are_correctly_ordered_with_different_separators(
        self, parser, store
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
        assert store.load() == {}

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


class TestSectionMarker:
    def test_options_serialize_options(self) -> None:
        section_header = SectionMarker.from_headerline(
            b"<<<"
            + b":".join(
                (
                    b"section",
                    b"cached(1,2)",
                    b"encoding(ascii)",
                    b"nostrip()",
                    b"persist(42)",
                    b"sep(124)",
                )
            )
            + b">>>"
        )
        assert section_header == SectionMarker.from_headerline(str(section_header).encode("ascii"))

    def test_options_deserialize_defaults(self) -> None:
        section_header = SectionMarker.from_headerline(b"<<<section>>>")
        other_header = SectionMarker.from_headerline(str(section_header).encode("ascii"))
        assert section_header == other_header
        assert str(section_header) == str(other_header)

    @pytest.mark.parametrize(
        "headerline, section_name, section_options",
        [
            ("norris", SectionName("norris"), {}),
            ("norris:chuck", SectionName("norris"), {"chuck": None}),
            (
                "my_section:sep(0):cached(23,42)",
                SectionName("my_section"),
                {"sep": "0", "cached": "23,42"},
            ),
            ("my.section:sep(0):cached(23,42)", None, {}),  # invalid section name
            ("", None, {}),  # invalid section name
        ],
    )  # yapf: disable
    def test_options_from_headerline(self, headerline, section_name, section_options) -> None:
        try:
            SectionMarker.from_headerline(
                f"<<<{headerline}>>>".encode("ascii")
            ) == (  # type: ignore[comparison-overlap]
                section_name,
                section_options,
            )
        except ValueError:
            assert section_name is None

    def test_options_decode_values(self) -> None:
        section_header = SectionMarker.from_headerline(
            b"<<<"
            + b":".join(
                (
                    b"name",
                    b"cached(1,2)",
                    b"encoding(ascii)",
                    b"nostrip()",
                    b"persist(42)",
                    b"sep(124)",
                )
            )
            + b">>>"
        )
        assert section_header.name == SectionName("name")
        assert section_header.cached == (1, 2)
        assert section_header.encoding == "ascii"
        assert section_header.nostrip is True
        assert section_header.persist == 42
        assert section_header.separator == "|"

    def test_options_decode_defaults(self) -> None:
        section_header = SectionMarker.from_headerline(b"<<<name>>>")
        assert section_header.name == SectionName("name")
        assert section_header.cached is None
        assert section_header.encoding == "utf-8"
        assert section_header.nostrip is False
        assert section_header.persist is None
        assert section_header.separator is None


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
            check_intervals={},
            keep_outdated=True,
            logger=logging.Logger("test"),
        )

    def test_empty_raw_data(self, parser) -> None:
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

    def test_no_cache(self, parser, sections) -> None:
        host_sections = parser.parse(sections, selection=NO_SELECTION)
        assert host_sections.sections == sections
        assert host_sections.cache_info == {}
        assert not host_sections.piggybacked_raw_data

    def test_with_persisted_sections(self, parser, sections, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        monkeypatch.setattr(parser, "check_intervals", defaultdict(lambda: 33))
        monkeypatch.setattr(
            SectionStore,
            "load",
            lambda self: PersistedSections[AgentRawDataSection](
                {
                    SectionName("persisted"): (42, 69, [["content"]]),
                }
            ),
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
    def __init__(self, path, sections, *, logger) -> None:
        super().__init__(path, logger=logger)
        assert isinstance(sections, PersistedSections)
        self._sections = sections

    def store(self, sections):
        self._sections = copy.copy(sections)

    def load(self):
        return copy.copy(self._sections)


class TestAgentPersistentSectionHandling:
    @pytest.fixture
    def logger(self):
        return logging.getLogger("test")

    def test_update_with_empty_store_and_empty_raw_data(self, logger) -> None:
        section_store = MockStore(
            "/dev/null",
            PersistedSections[AgentRawDataSection]({}),
            logger=logger,
        )
        raw_data = AgentRawData(b"")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_store_and_empty_raw_data(self, logger) -> None:
        section_store = MockStore(
            "/dev/null",
            PersistedSections[AgentRawDataSection](
                {
                    SectionName("stored"): (0, 0, []),
                }
            ),
            logger=logger,
        )
        raw_data = AgentRawData(b"")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("stored"): []}
        assert ahs.cache_info == {SectionName("stored"): (0, 0)}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection](
            {
                SectionName("stored"): (0, 0, []),
            }
        )

    def test_update_with_empty_store_and_raw_data(self, logger) -> None:
        raw_data = AgentRawData(b"<<<fresh>>>")
        section_store = MockStore(
            "/dev/null",
            PersistedSections[AgentRawDataSection]({}),
            logger=logger,
        )
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("fresh"): []}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_store_and_non_persisting_raw_data(self, logger) -> None:
        section_store = MockStore(
            "/dev/null",
            PersistedSections[AgentRawDataSection](
                {
                    SectionName("stored"): (0, 0, []),
                }
            ),
            logger=logger,
        )
        raw_data = AgentRawData(b"<<<fresh>>>")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("fresh"): [],
            SectionName("stored"): [],
        }
        assert ahs.cache_info == {SectionName("stored"): (0, 0)}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection](
            {
                SectionName("stored"): (0, 0, []),
            }
        )

    def test_update_with_store_and_persisting_raw_data(self, logger, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))
        section_store = MockStore(
            "/dev/null",
            PersistedSections[AgentRawDataSection](
                {
                    SectionName("stored"): (0, 0, [["canned", "section"]]),
                }
            ),
            logger=logger,
        )
        raw_data = AgentRawData(b"<<<fresh:persist(10)>>>\nhello section")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
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
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection](
            {
                SectionName("stored"): (0, 0, [["canned", "section"]]),
                SectionName("fresh"): (1000, 10, [["hello", "section"]]),
            }
        )

    def test_update_store_with_newest(self, logger) -> None:
        section_store = MockStore(
            "/dev/null",
            PersistedSections[AgentRawDataSection](
                {
                    SectionName("section"): (0, 0, [["oldest"]]),
                }
            ),
            logger=logger,
        )
        raw_data = AgentRawData(b"<<<section>>>\nnewest")
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            check_interval=0,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("section"): [["newest"]]}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection](
            {
                SectionName("section"): (0, 0, [["oldest"]]),
            }
        )

    def test_keep_outdated_false(self, logger, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        raw_data = AgentRawData(b"<<<another_section>>>")
        section_store = MockStore(
            "/dev/null",
            PersistedSections[AgentRawDataSection](
                {
                    SectionName("section"): (500, 600, []),
                }
            ),
            logger=logger,
        )
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            check_interval=42,
            keep_outdated=False,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {SectionName("another_section"): []}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_keep_outdated_true(self, logger, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        raw_data = AgentRawData(b"<<<another_section>>>")
        section_store = MockStore(
            "/dev/null",
            PersistedSections[AgentRawDataSection](
                {
                    SectionName("section"): (500, 600, []),
                }
            ),
            logger=logger,
        )
        parser = AgentParser(
            HostName("testhost"),
            section_store,
            check_interval=42,
            keep_outdated=True,
            translation={},
            encoding_fallback="ascii",
            simulation=False,
            logger=logger,
        )

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {
            SectionName("another_section"): [],
            SectionName("section"): [],
        }
        assert ahs.cache_info == {SectionName("section"): (500, 100)}
        assert ahs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[AgentRawDataSection](
            {
                SectionName("section"): (500, 600, []),
            }
        )


class TestSNMPPersistedSectionHandling:
    @pytest.fixture
    def logger(self):
        return logging.getLogger("test")

    def test_update_with_empty_store_and_persisted(self, logger) -> None:
        section_store = MockStore(
            "/dev/null",
            PersistedSections[SNMPRawDataSection]({}),
            logger=logger,
        )
        raw_data: SNMPRawData = {}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            check_intervals={},
            keep_outdated=True,
            logger=logger,
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_empty_persisted(self, logger) -> None:
        section_store = MockStore(
            "/dev/null",
            PersistedSections[SNMPRawDataSection](
                {
                    SectionName("stored"): (0, 0, [["old"]]),
                }
            ),
            logger=logger,
        )
        raw_data: SNMPRawData = {}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            check_intervals={},
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

    def test_update_with_empty_store(self, logger) -> None:
        section_store = MockStore(
            "/dev/null",
            PersistedSections[SNMPRawDataSection]({}),
            logger=logger,
        )
        _new: Sequence[SNMPRawDataSection] = [["new"]]  # For the type checker only
        raw_data: SNMPRawData = {SectionName("fresh"): _new}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            check_intervals={},
            keep_outdated=True,
            logger=logger,
        )

        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("fresh"): [["new"]]}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_update_with_persisted_and_store(self, logger) -> None:
        section_store = MockStore(
            "/dev/null",
            PersistedSections[SNMPRawDataSection](
                {
                    SectionName("stored"): (0, 0, [["old"]]),
                }
            ),
            logger=logger,
        )
        _new: Sequence[SNMPRawDataSection] = [["new"]]  # For the type checker only
        raw_data: SNMPRawData = {SectionName("fresh"): _new}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            check_intervals={},
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

    def test_check_intervals_updates_persisted(self, logger, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        section_store = MockStore(
            "/dev/null",
            PersistedSections[SNMPRawDataSection](
                {
                    SectionName("section"): (0, 0, [["old"]]),
                }
            ),
            logger=logger,
        )
        _new: Sequence[SNMPRawDataSection] = [["new"]]  # For the type checker only
        raw_data: SNMPRawData = {SectionName("section"): _new}
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            check_intervals={SectionName("section"): 42},
            keep_outdated=True,
            logger=logger,
        )
        shs = parser.parse(raw_data, selection=NO_SELECTION)
        assert shs.sections == {SectionName("section"): [["new"]]}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == PersistedSections[SNMPRawDataSection](
            {
                SectionName("section"): (1000, 1042, [["new"]]),
            }
        )

    def test_keep_outdated_false(self, logger, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        section_store = MockStore(
            "/dev/null",
            PersistedSections[SNMPRawDataSection](
                {
                    SectionName("section"): (500, 600, [["old"]]),
                }
            ),
            logger=logger,
        )
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            check_intervals={SectionName("section"): 42},
            keep_outdated=False,
            logger=logger,
        )
        shs = parser.parse({}, selection=NO_SELECTION)
        assert shs.sections == {}
        assert shs.cache_info == {}
        assert shs.piggybacked_raw_data == {}
        assert section_store.load() == {}

    def test_keep_outdated_true(self, logger, monkeypatch) -> None:
        monkeypatch.setattr(time, "time", lambda c=itertools.count(1000, 50): next(c))

        section_store = MockStore(
            "/dev/null",
            PersistedSections[SNMPRawDataSection](
                {
                    SectionName("section"): (500, 600, [["old"]]),
                }
            ),
            logger=logger,
        )
        parser = SNMPParser(
            HostName("testhost"),
            section_store,
            check_intervals={SectionName("section"): 42},
            keep_outdated=True,
            logger=logger,
        )
        shs = parser.parse({}, selection=NO_SELECTION)
        assert shs.sections == {SectionName("section"): [["old"]]}
        assert shs.cache_info == {
            SectionName("section"): (500, 100),
        }
        assert shs.piggybacked_raw_data == {}
        assert not section_store.load() == PersistedSections[SNMPRawDataSection](
            {
                SectionName("section"): (1000, 1042, [["old"]]),
            }
        )


class TestMarkers:
    @pytest.mark.parametrize("line", [b"<<<x>>>", b"<<<x:cached(10, 5)>>>"])
    def test_section_header(self, line) -> None:
        assert SectionMarker.is_header(line) is True
        assert SectionMarker.is_footer(line) is False
        assert PiggybackMarker.is_header(line) is False
        assert PiggybackMarker.is_footer(line) is False

    @pytest.mark.parametrize("line", [b"<<<>>>", b"<<<:cached(10, 5)>>>"])
    def test_section_footer(self, line) -> None:
        assert SectionMarker.is_header(line) is False
        assert SectionMarker.is_footer(line) is True
        assert PiggybackMarker.is_header(line) is False
        assert PiggybackMarker.is_footer(line) is False

    def test_piggybacked_host_header(self) -> None:
        line = b"<<<<x>>>>"
        assert SectionMarker.is_header(line) is False
        assert SectionMarker.is_footer(line) is False
        assert PiggybackMarker.is_header(line) is True
        assert PiggybackMarker.is_footer(line) is False

    def test_piggybacked_host_footer(self) -> None:
        line = b"<<<<>>>>"
        assert SectionMarker.is_header(line) is False
        assert SectionMarker.is_footer(line) is False
        assert PiggybackMarker.is_header(line) is False
        assert PiggybackMarker.is_footer(line) is True
