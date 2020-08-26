#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Cache implementations for the data sources."""

import logging
import time
from pathlib import Path
from typing import Generic, Union

import cmk.utils.store as store
from cmk.utils.type_defs import SectionName

from cmk.base.check_utils import TPersistedSections


class SectionStore(Generic[TPersistedSections]):
    def __init__(self, path: Union[str, Path], logger: logging.Logger) -> None:
        super(SectionStore, self).__init__()
        self.path = Path(path)
        self._logger = logger

    def store(self, sections: TPersistedSections) -> None:
        if not sections:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        store.save_object_to_file(self.path, {str(k): v for k, v in sections.items()}, pretty=False)
        self._logger.debug("Stored persisted sections: %s", ", ".join(str(s) for s in sections))

    # TODO: This is not race condition free when modifying the data. Either remove
    # the possible write here and simply ignore the outdated sections or lock when
    # reading and unlock after writing
    def load(self, keep_outdated: bool) -> TPersistedSections:
        raw_sections_data = store.load_object_from_file(self.path, default={})
        sections: TPersistedSections = {  # type: ignore[assignment]
            SectionName(k): v for k, v in raw_sections_data.items()
        }
        if not keep_outdated:
            sections = self._filter(sections)

        if not sections:
            self._logger.debug("No persisted sections loaded")
            self.path.unlink(missing_ok=True)

        return sections

    def _filter(self, sections: TPersistedSections) -> TPersistedSections:
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
