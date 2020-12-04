#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Persisted sections type and store."""

import logging
import time
from pathlib import Path
from typing import (
    Final,
    Generic,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

import cmk.utils.store as _store
from cmk.utils.type_defs import AgentRawDataSection, SectionName

from cmk.snmplib.type_defs import SNMPRawDataSection

__all__ = ["ABCRawDataSection", "PersistedSections", "SectionStore", "TRawDataSection"]

# ABCRawDataSection is wrong from a typing point of view.
# AgentRawDataSection and SNMPRawDataSection are not correct either.
ABCRawDataSection = Union[AgentRawDataSection, SNMPRawDataSection]
TRawDataSection = TypeVar("TRawDataSection", bound=ABCRawDataSection)


class PersistedSections(
        Generic[TRawDataSection],
        MutableMapping[SectionName, Tuple[int, int, TRawDataSection]],
):
    __slots__ = ("_store",)

    def __init__(self, store: MutableMapping[SectionName, Tuple[int, int, TRawDataSection]]):
        self._store = store

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._store)

    def __getitem__(self, key: SectionName) -> Tuple[int, int, TRawDataSection]:
        return self._store.__getitem__(key)

    def __setitem__(self, key: SectionName, value: Tuple[int, int, TRawDataSection]) -> None:
        return self._store.__setitem__(key, value)

    def __delitem__(self, key: SectionName) -> None:
        return self._store.__delitem__(key)

    def __iter__(self) -> Iterator[SectionName]:
        return self._store.__iter__()

    def __len__(self) -> int:
        return self._store.__len__()

    @classmethod
    def from_sections(
        cls,
        sections: Mapping[SectionName, TRawDataSection],
        interval_lookup: Mapping[SectionName, Optional[int]],
        *,
        cached_at: int,
    ) -> "PersistedSections[TRawDataSection]":
        self = cls({})
        for section_name, section_content in sections.items():
            fetch_interval = interval_lookup[section_name]
            if fetch_interval is None:
                continue
            self[section_name] = (cached_at, fetch_interval, section_content)

        return self

    def update_and_store(
        self,
        section_store: "SectionStore[TRawDataSection]",
    ) -> None:
        stored = section_store.load()
        if self != stored:
            self.update(stored)
            section_store.store(self)


class SectionStore(Generic[TRawDataSection]):
    def __init__(
        self,
        path: Union[str, Path],
        *,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.path: Final = Path(path)
        self.keep_outdated: Final = keep_outdated
        self._logger: Final = logger

    def store(self, sections: PersistedSections[TRawDataSection]) -> None:
        if not sections:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        _store.save_object_to_file(self.path, {str(k): v for k, v in sections.items()},
                                   pretty=False)
        self._logger.debug("Stored persisted sections: %s", ", ".join(str(s) for s in sections))

    # TODO: This is not race condition free when modifying the data. Either remove
    # the possible write here and simply ignore the outdated sections or lock when
    # reading and unlock after writing
    def load(self) -> PersistedSections[TRawDataSection]:
        raw_sections_data = _store.load_object_from_file(self.path, default={})
        sections: PersistedSections[TRawDataSection] = {  # type: ignore[assignment]
            SectionName(k): v for k, v in raw_sections_data.items()
        }
        if not self.keep_outdated:
            sections = self._filter(sections)

        if not sections:
            self._logger.debug("No persisted sections loaded")
            self.path.unlink(missing_ok=True)

        return sections

    def _filter(
        self,
        sections: PersistedSections[TRawDataSection],
    ) -> PersistedSections[TRawDataSection]:
        now = time.time()
        for section_name, entry in list(sections.items()):
            if len(entry) == 2:
                persisted_until = entry[0]
            else:
                persisted_until = entry[1]

            if now > persisted_until:
                self._logger.debug("Persisted section %s is outdated by %d seconds. Skipping it.",
                                   section_name, now - persisted_until)
                del sections[section_name]
        return sections
