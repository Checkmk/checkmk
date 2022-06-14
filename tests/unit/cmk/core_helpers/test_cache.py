#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
import logging
from typing import Sequence

from cmk.utils.type_defs import SectionName

from cmk.core_helpers.cache import MaxAge, PersistedSections, SectionStore
from cmk.core_helpers.type_defs import AgentRawDataSection, Mode


class MockStore:
    def __init__(self, data):
        super().__init__()
        self._data = data

    def store(self, data):
        self._data = copy.copy(data)

    def load(self):
        return copy.copy(self._data)


class TestPersistedSections:
    def test_from_sections(self) -> None:
        section_a = SectionName("section_a")
        content_a: Sequence[AgentRawDataSection] = [["first", "line"], ["second", "line"]]
        section_b = SectionName("section_b")
        content_b: Sequence[AgentRawDataSection] = [["third", "line"], ["forth", "line"]]
        sections = {section_a: content_a, section_b: content_b}
        cached_at = 69
        fetch_interval = 42
        persist_info = {section_a: (cached_at, cached_at + fetch_interval), section_b: None}

        persisted_sections = PersistedSections[AgentRawDataSection].from_sections(
            sections=sections,
            lookup_persist=persist_info.get,
        )

        assert persisted_sections == {  # type: ignore[comparison-overlap]
            section_a: (cached_at, cached_at + fetch_interval, content_a)
        }


class TestSectionStore:
    def test_repr(self) -> None:
        assert isinstance(
            repr(
                SectionStore(
                    "/dev/null",
                    logger=logging.getLogger("test"),
                )
            ),
            str,
        )


class TestMaxAge:
    def test_repr(self) -> None:
        max_age = MaxAge(checking=42, discovery=69, inventory=1337)
        assert isinstance(repr(max_age), str)

    def test_serialize(self) -> None:
        max_age = MaxAge(checking=42, discovery=69, inventory=1337)
        assert MaxAge(*json.loads(json.dumps(max_age))) == max_age

    def test_get(self) -> None:
        max_age = MaxAge(checking=42, discovery=69, inventory=1337)
        assert max_age.get(Mode.CHECKING) == 42
        assert max_age.get(Mode.DISCOVERY) == 69
        assert max_age.get(Mode.INVENTORY) == 1337
        assert max_age.get(Mode.NONE) == 0
