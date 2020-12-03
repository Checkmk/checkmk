#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

import pytest  # type: ignore[import]

from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.type_defs import SectionName

from cmk.snmplib.type_defs import SNMPRawData

from cmk.base.checkers.host_sections import PersistedSections, SectionStore
from cmk.base.checkers.snmp import SNMPParser
from cmk.base.checkers.type_defs import NO_SELECTION


class TestSNMPParser:
    @pytest.fixture
    def hostname(self):
        return "hostname"

    @pytest.fixture(autouse=True)
    def scenario_fixture(self, hostname, monkeypatch):
        Scenario().add_host(hostname).apply(monkeypatch)

    @pytest.fixture
    def parser(self, hostname):
        return SNMPParser(
            hostname,
            SectionStore(
                "/tmp/store",
                keep_outdated=True,
                logger=logging.Logger("test"),
            ),
            logging.Logger("test"),
        )

    def test_empty_raw_data(self, parser):
        raw_data = SNMPRawData({})

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

    def test_no_cache(self, parser, sections):
        host_sections = parser.parse(SNMPRawData(sections), selection=NO_SELECTION)
        assert host_sections.sections == sections
        assert host_sections.cache_info == {}
        assert not host_sections.piggybacked_raw_data

    def test_with_persisted_sections(self, parser, sections, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1000)
        monkeypatch.setattr(
            parser.host_config,
            "snmp_fetch_interval",
            lambda section_name: 33,
        )
        monkeypatch.setattr(
            SectionStore, "load", lambda self: PersistedSections({
                SectionName("persisted"): (42, 69, [["content"]]),
            }))
        # Patch IO:
        monkeypatch.setattr(SectionStore, "store", lambda self, sections: None)

        raw_data = SNMPRawData(sections)

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        all_sections = sections.copy()
        all_sections[SectionName("persisted")] = [["content"]]
        assert ahs.sections == all_sections
        assert ahs.cache_info == {SectionName("persisted"): (42, 27)}
        assert ahs.piggybacked_raw_data == {}
