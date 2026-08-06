#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Callable, Mapping, MutableMapping
from pathlib import Path
from typing import Final, override

import cmk.ccc.store as _store
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.plugins import SectionName

__all__ = ["SectionStore"]
PersistedSectionDir = Path
logger = logging.getLogger(__name__)


class SectionStore[T]:
    def __init__(
        self,
        path: PersistedSectionDir,
    ) -> None:
        super().__init__()
        self.path: Final = Path(path)

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path!r})"

    @staticmethod
    def make_persisted_section_dir(
        host_name: HostName, *, ident: str, section_cache_path: Path
    ) -> PersistedSectionDir:
        return section_cache_path / "persisted_sections" / ident / str(host_name)

    def store(self, sections: MutableMapping[SectionName, tuple[int, int, T]]) -> None:
        if not sections:
            logger.debug("No persisted sections")
            self.path.unlink(missing_ok=True)
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        _store.save_object_to_pickle_file(
            self.path,
            {str(k): v for k, v in sections.items()},
        )
        logger.debug(
            "Stored persisted sections: %(sections)s",
            {"sections": ", ".join(str(s) for s in sections)},
        )

    def load(self) -> MutableMapping[SectionName, tuple[int, int, T]]:
        raw_sections_data = _store.load_object_from_pickle_file(self.path, default={})
        return {SectionName(k): v for k, v in raw_sections_data.items()}

    def update(
        self,
        sections: Mapping[SectionName, T],
        cache_info: MutableMapping[SectionName, tuple[int, int]],
        lookup_persist: Mapping[SectionName, int | None],
        section_outdated: Callable[[int, int], bool],
        now: int,
        keep_outdated: bool,
    ) -> Mapping[SectionName, T]:
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
        sections: Mapping[SectionName, T],
        lookup_persist: Mapping[SectionName, int | None],
        section_outdated: Callable[[int, int], bool],
        *,
        now: int,
        keep_outdated: bool,
    ) -> MutableMapping[SectionName, tuple[int, int, T]]:
        # TODO: This is not race condition free when modifying the data. Either remove
        # the possible write here and simply ignore the outdated sections or lock when
        # reading and unlock after writing
        persisted_sections = self.load()

        new_sections = {
            section_name: (now, persist_info, section_content)
            for section_name, section_content in sections.items()
            if (persist_info := lookup_persist.get(section_name)) is not None
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
        sections: Mapping[SectionName, T],
        cache_info: MutableMapping[SectionName, tuple[int, int]],
        persisted_sections: MutableMapping[SectionName, tuple[int, int, T]],
    ) -> Mapping[SectionName, T]:
        cache_info.update(
            {
                section_name: (created_at, valid_until - created_at)
                for section_name, (created_at, valid_until, *_rest) in persisted_sections.items()
                if section_name not in sections
            }
        )
        result = dict(sections.items())
        for section_name, entry in persisted_sections.items():
            # Don't overwrite sections that have been received from the source with this call
            if section_name in sections:
                logger.debug(
                    "Skipping persisted section %(section_name)r, live data available",
                    {"section_name": section_name},
                )
                continue

            logger.debug("Using persisted section %(section_name)r", {"section_name": section_name})
            result[section_name] = entry[-1]
        return result
