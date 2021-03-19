#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import logging
from typing import Mapping

import pytest  # type: ignore[import]

from cmk.utils.type_defs import SectionName

from cmk.core_helpers.cache import ABCRawDataSection, PersistedSections, SectionStore
from cmk.core_helpers.host_sections import HostSections


class MockStore(SectionStore):
    # pylint: disable=super-init-not-called, arguments-differ
    def __init__(self, data):
        self._data = data

    def store(self, data):
        self._data = copy.copy(data)

    def load(self):
        return copy.copy(self._data)


class TestPersistentSectionHandling:
    @pytest.fixture
    def host_sections(self):
        return HostSections()

    @pytest.fixture
    def logger(self):
        return logging.Logger("tests")

    def test_update_with_empty_store_and_persisted(self, host_sections, logger):
        sections: Mapping[SectionName, ABCRawDataSection] = {}
        section_store = MockStore(PersistedSections({}))

        host_sections.add_persisted_sections(
            sections,
            section_store=section_store,
            fetch_interval=lambda section_name: 0,
            now=0,
            keep_outdated=True,
            logger=logger,
        )

        assert not host_sections.sections

    def test_update_with_empty_persisted(self, host_sections, logger):
        stored = SectionName("stored")

        sections: Mapping[SectionName, ABCRawDataSection] = {}
        section_store = MockStore(PersistedSections({stored: (0, 0, [])}))

        host_sections.add_persisted_sections(
            sections,
            section_store=section_store,
            fetch_interval=lambda section_name: 0,
            now=0,
            keep_outdated=True,
            logger=logger,
        )

        assert stored in host_sections.sections

    def test_update_with_empty_store(self, host_sections, logger):
        fresh = SectionName("fresh")

        sections: Mapping[SectionName, ABCRawDataSection] = {fresh: [[""]]}
        section_store = MockStore(PersistedSections({}))

        host_sections.add_persisted_sections(
            sections,
            section_store=section_store,
            fetch_interval=lambda section_name: 0,
            now=0,
            keep_outdated=True,
            logger=logger,
        )

        assert fresh in host_sections.sections

    def test_update_with_persisted_and_store(self, host_sections, logger):
        stored = SectionName("stored")
        fresh = SectionName("fresh")

        sections: Mapping[SectionName, ABCRawDataSection] = {fresh: [[""]]}
        section_store = MockStore(PersistedSections({stored: (0, 0, [])}))

        host_sections.add_persisted_sections(
            sections,
            section_store=section_store,
            fetch_interval=lambda section_name: 0,
            now=0,
            keep_outdated=True,
            logger=logger,
        )

        assert stored in host_sections.sections
        assert fresh in host_sections.sections

    def test_update_store_with_newest(self, host_sections, logger):
        section = SectionName("section")

        sections = {section: [["newest"]]}
        section_store = MockStore(PersistedSections({
            section: (0, 0, [["oldest"]]),
        }))

        host_sections.add_persisted_sections(
            sections,
            section_store=section_store,
            fetch_interval=lambda section_name: 0,
            now=0,
            keep_outdated=True,
            logger=logger,
        )

        assert host_sections.sections[section] == [["newest"]]

    def test_do_not_keep_outdated(self, host_sections, logger):
        stored = SectionName("stored")

        sections: Mapping[SectionName, ABCRawDataSection] = {}
        section_store = MockStore(PersistedSections({stored: (0, 0, [])}))

        host_sections.add_persisted_sections(
            sections,
            section_store=section_store,
            fetch_interval=lambda section_name: 0,
            now=1,
            keep_outdated=False,
            logger=logger,
        )

        assert not host_sections.sections
