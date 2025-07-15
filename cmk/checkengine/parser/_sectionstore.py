#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Final, Generic, TypeVar

import cmk.ccc.store as _store
from cmk.utils.sectionname import MutableSectionMap, SectionMap, SectionName

__all__ = ["SectionStore"]

_T = TypeVar("_T")


class SectionStore(Generic[_T]):
    def __init__(
        self,
        path: str | Path,
        *,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.path: Final = Path(path)
        self._logger: Final = logger

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path!r}, logger={self._logger!r})"

    def store(self, sections: MutableSectionMap[tuple[int, int, _T]]) -> None:
        if not sections:
            self._logger.debug("No persisted sections")
            self.path.unlink(missing_ok=True)
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        _store.save_object_to_pickle_file(
            self.path,
            {str(k): v for k, v in sections.items()},
        )
        self._logger.debug("Stored persisted sections: %s", ", ".join(str(s) for s in sections))

    def load(self) -> MutableSectionMap[tuple[int, int, _T]]:
        raw_sections_data = _store.load_object_from_pickle_file(self.path, default={})
        return {SectionName(k): v for k, v in raw_sections_data.items()}

    def update(
        self,
        sections: SectionMap[_T],
        cache_info: MutableSectionMap[tuple[int, int]],
        lookup_persist: Callable[[SectionName], tuple[int, int] | None],
        section_outdated: Callable[[int, int], bool],
        now: int,
        keep_outdated: bool,
    ) -> SectionMap[_T]:
        persisted_sections = self._update(
            sections,
            lookup_persist,
            section_outdated,
            now=now,
            keep_outdated=keep_outdated,
        )
        return self._add_persisted_sections(
            sections,
            cache_info,
            persisted_sections,
        )

    def _update(
        self,
        sections: SectionMap[_T],
        lookup_persist: Callable[[SectionName], tuple[int, int] | None],
        section_outdated: Callable[[int, int], bool],
        *,
        now: int,
        keep_outdated: bool,
    ) -> MutableSectionMap[tuple[int, int, _T]]:
        # TODO: This is not race condition free when modifying the data. Either remove
        # the possible write here and simply ignore the outdated sections or lock when
        # reading and unlock after writing
        persisted_sections = self.load()

        new_sections = {
            section_name: persist_info + (section_content,)
            for section_name, section_content in sections.items()
            if (persist_info := lookup_persist(section_name)) is not None
        }
        store_sections = bool(new_sections)
        persisted_sections.update(new_sections)

        if not keep_outdated:
            for section_name in tuple(persisted_sections):
                (_created_at, valid_until, _section_content) = persisted_sections[section_name]
                if section_outdated(valid_until, now):
                    store_sections = True
                    del persisted_sections[section_name]

        if store_sections:
            self.store(persisted_sections)
        return persisted_sections

    def _add_persisted_sections(
        self,
        sections: SectionMap[_T],
        cache_info: MutableSectionMap[tuple[int, int]],
        persisted_sections: MutableSectionMap[tuple[int, int, _T]],
    ) -> SectionMap[_T]:
        cache_info.update(
            {
                section_name: (created_at, valid_until - created_at)
                for section_name, (created_at, valid_until, *_rest) in persisted_sections.items()
                if section_name not in sections
            }
        )
        result: MutableSectionMap[_T] = dict(sections.items())
        for section_name, entry in persisted_sections.items():
            # Don't overwrite sections that have been received from the source with this call
            if section_name in sections:
                self._logger.debug(
                    "Skipping persisted section %r, live data available",
                    section_name,
                )
                continue

            self._logger.debug("Using persisted section %r", section_name)
            result[section_name] = entry[-1]
        return result
