#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Cache implementations for the data sources."""

import errno
import logging
import os
import time
from pathlib import Path
from typing import Optional, Union

import cmk.utils
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import SectionName

import cmk.base.config as config
from cmk.base.check_utils import BoundedAbstractPersistedSections, BoundedAbstractRawData


class SectionStore:
    def __init__(self, path: str, logger: logging.Logger) -> None:
        super(SectionStore, self).__init__()
        self.path = path
        self._logger = logger

    def store(self, sections):
        # type: (BoundedAbstractPersistedSections) -> None
        if not sections:
            return

        try:
            os.makedirs(os.path.dirname(self.path))
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

        store.save_object_to_file(self.path, {str(k): v for k, v in sections.items()}, pretty=False)
        self._logger.debug("Stored persisted sections: %s", ", ".join(str(s) for s in sections))

    # TODO: This is not race condition free when modifying the data. Either remove
    # the possible write here and simply ignore the outdated sections or lock when
    # reading and unlock after writing
    def load(self, keep_outdated):
        # type: (bool) -> BoundedAbstractPersistedSections
        raw_sections_data = store.load_object_from_file(self.path, default={})
        sections: BoundedAbstractPersistedSections = {  # type: ignore[assignment]
            SectionName(k): v for k, v in raw_sections_data.items()
        }
        if not keep_outdated:
            sections = self._filter(sections)

        if not sections:
            self._logger.debug("No persisted sections loaded")
            try:
                os.remove(self.path)
            except OSError:
                pass

        return sections

    def _filter(self, sections):
        # type: (BoundedAbstractPersistedSections) -> BoundedAbstractPersistedSections
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


class FileCache:
    def __init__(
            self,
            path,  # type: Union[str, Path]
            max_cachefile_age,  # type: Optional[int]
            is_agent_cache_disabled,  # type: bool
            may_use_cache_file,  # type: bool
            use_outdated_cache_file,  # type: bool
            from_cache_file,
            to_cache_file,
            logger,  # type: logging.Logger
    ):
        # type (...) -> None
        super(FileCache, self).__init__()
        self.path = Path(path)
        self._max_cachefile_age = max_cachefile_age
        self._is_agent_cache_disabled = is_agent_cache_disabled
        self._may_use_cache_file = may_use_cache_file
        self._use_outdated_cache_file = use_outdated_cache_file
        self._from_cache_file = from_cache_file
        self._to_cache_file = to_cache_file
        self._logger = logger

    def read(self):
        # type: () -> Optional[BoundedAbstractRawData]
        assert self._max_cachefile_age is not None
        if not self.path.exists():
            self._logger.debug("Not using cache (Does not exist)")
            return None

        if self._is_agent_cache_disabled:
            self._logger.debug("Not using cache (Cache usage disabled)")
            return None

        if not self._may_use_cache_file and not config.simulation_mode:
            self._logger.debug("Not using cache (Don't try it)")
            return None

        may_use_outdated = config.simulation_mode or self._use_outdated_cache_file
        cachefile_age = cmk.utils.cachefile_age(self.path)
        if not may_use_outdated and cachefile_age > self._max_cachefile_age:
            self._logger.debug("Not using cache (Too old. Age is %d sec, allowed is %s sec)",
                               cachefile_age, self._max_cachefile_age)
            return None

        # TODO: Use some generic store file read function to generalize error handling,
        # but there is currently no function that simply reads data from the file
        result = self.path.read_bytes()
        if not result:
            self._logger.debug("Not using cache (Empty)")
            return None

        self._logger.log(VERBOSE, "Using data from cache file %s", self.path)
        return self._from_cache_file(result)

    def write(self, raw_data):
        # type: (BoundedAbstractRawData) -> None
        if self._is_agent_cache_disabled:
            self._logger.debug("Not writing data to cache file (Cache usage disabled)")
            return

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise MKGeneralException("Cannot create directory %r: %s" % (self.path.parent, e))

        self._logger.debug("Write data to cache file %s", self.path)
        try:
            store.save_file(self.path, self._to_cache_file(raw_data))
        except Exception as e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (self.path, e))
