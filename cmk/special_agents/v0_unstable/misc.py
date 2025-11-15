#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Place for common code shared among different Check_MK special agents

Please don't add code to this file and allow new components to have a module for their own.
"""

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import abc
import datetime
import json
import logging
import time
from typing import Any

from cmk.server_side_programs.v1_unstable import Storage


def _datetime_serializer(obj):
    """Custom serializer to pass to json dump functions"""
    if isinstance(obj, datetime.datetime):
        return str(obj)
    # fall back to json default behaviour:
    raise TypeError("%r is not JSON serializable" % obj)


class DataCache(abc.ABC):
    """
    Attention! A user may configure multiple special agents per Checkmk instance.
    Most of the time you don't want to share the Cache between those configurations.
    Normally you should use the hostname as part of the cache_file_name or cache_file_dir.
    """

    def __init__(self, *, host_name: str, agent: str, key: str, debug: bool = False) -> None:
        self._storage = Storage(host_name, agent)
        self._key = key
        self.debug = debug

    def _read_storage(self) -> tuple[float, str] | None:
        if (raw := self._storage.read(self._key, None)) is None:
            return None

        try:
            raw_timestamp, raw_content = raw.split("\n", 1)
            return float(raw_timestamp), raw_content
        except ValueError:
            logging.warning("Corrupted stograge content. Removing it.")
            self._storage.unset(self._key)
        return None

    def _write_storage(self, raw_content: str) -> None:
        self._storage.write(self._key, f"{time.time()}\n{raw_content}")

    @property
    @abc.abstractmethod
    def cache_interval(self) -> int:
        """
        Return the time for how long cached data is valid
        """

    @abc.abstractmethod
    def get_validity_from_args(self, *args: Any) -> bool:
        """
        Decide whether we need to update the cache due to new arguments
        """

    @abc.abstractmethod
    def get_live_data(self, *args: Any) -> Any:
        """
        This is the function that will be called if no cached data can be found.
        """

    @property
    def cache_timestamp(self) -> float | None:
        return None if (read := self._read_storage()) is None else read[0]

    def _cache_is_valid(self):
        mtime = self.cache_timestamp
        if mtime is None:
            return False

        age = time.time() - mtime
        if 0 < age < self.cache_interval:
            return True

        if age < 0:
            logging.info("Cache file from future considered invalid.")
        return False

    def get_cached_data(self):
        if (read := self._read_storage()) is None:
            # raising here is silly, but I am refactoring and want to
            # keep the changes as small as possible.
            raise FileNotFoundError(self._key)

        _raw_timestamp, raw_content = read
        try:
            content = json.loads(raw_content)
        except ValueError as exc:
            logging.info("Cannot load raw content: %s", exc)
            raise
        return content

    def get_data(self, *args, **kwargs):
        use_cache = kwargs.pop("use_cache", True)
        if use_cache and self.get_validity_from_args(*args) and self._cache_is_valid():
            try:
                return self.get_cached_data()
            except (OSError, ValueError) as exc:
                logging.info("Getting live data (failed to read from cache: %s).", exc)
                if self.debug:
                    raise

        live_data = self.get_live_data(*args)
        try:
            self._write_to_cache(live_data)
        except (OSError, TypeError) as exc:
            logging.info("Failed to write data to cache file: %s", exc)
            if self.debug:
                raise
        return live_data

    def _write_to_cache(self, raw_content):
        self._write_storage(json.dumps(raw_content, default=_datetime_serializer))
