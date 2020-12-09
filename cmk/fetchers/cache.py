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

    def filter(self, *, keep_outdated: bool) -> None:
        """Remove older entries from the database.

        Args:
            keep_outdated: Do not remove anything if True.

        """
        if keep_outdated:
            return

        now = time.time()
        for section_name, entry in list(self.items()):
            if len(entry) == 2:
                persisted_until = entry[0]
            else:
                persisted_until = entry[1]

            if now > persisted_until:
                # TODO(ml): Log deletions.
                del self[section_name]

    def update_and_store(
        self,
        section_store: "SectionStore[TRawDataSection]",
        *,
        keep_outdated: bool,
    ) -> None:
        # TODO: This is not race condition free when modifying the data. Either remove
        # the possible write here and simply ignore the outdated sections or lock when
        # reading and unlock after writing
        stored = section_store.load()
        if self == stored:
            return

        # Update the DB.
        stored.update(self)
        # Add stored sections to self.
        self.update(stored)
        # Now, self and stored must be equal.
        assert self == stored
        # Filter if requested
        self.filter(keep_outdated=keep_outdated)
        # Save the updated DB.
        section_store.store(self)


class SectionStore(Generic[TRawDataSection]):
    def __init__(
        self,
        path: Union[str, Path],
        *,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.path: Final = Path(path)
        self._logger: Final = logger

    def store(self, sections: PersistedSections[TRawDataSection]) -> None:
        if not sections:
            self._logger.debug("No persisted sections")
            self.path.unlink(missing_ok=True)
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        _store.save_object_to_file(
            self.path,
            {str(k): v for k, v in sections.items()},
            pretty=False,
        )
        self._logger.debug("Stored persisted sections: %s", ", ".join(str(s) for s in sections))

    def load(self) -> PersistedSections[TRawDataSection]:
        raw_sections_data = _store.load_object_from_file(self.path, default={})
        return PersistedSections[TRawDataSection](
            {SectionName(k): v for k, v in raw_sections_data.items()})
