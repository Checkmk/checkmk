#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Place for common code shared among different Check_MK special agents

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

Please don't add code to this file and allow new components to have a module for their own.
"""

import abc
import datetime
import json
import logging
import time
from pathlib import Path
from typing import Any

from cmk.ccc import store


def datetime_serializer(obj):
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

    def __init__(self, cache_file_dir: Path, cache_file_name: str, debug: bool = False) -> None:
        self._cache_file_dir = cache_file_dir
        self._cache_file = self._cache_file_dir / ("%s.cache" % cache_file_name)
        self.debug = debug

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
    def cache_timestamp(self):
        if not self._cache_file.exists():
            return None

        try:
            return self._cache_file.stat().st_mtime
        except FileNotFoundError:
            logging.info("No such file or directory %s (cache_timestamp)", self._cache_file)
            return None
        except OSError as exc:
            logging.info("Cannot calculate cache file age: %s", exc)
            raise

    def _cache_is_valid(self):
        mtime = self.cache_timestamp
        if mtime is None:
            return False

        age = time.time() - mtime
        if 0 < age < self.cache_interval:
            return True

        if age < 0:
            logging.info("Cache file from future considered invalid: %s", self._cache_file)
        else:
            logging.info("Cache file %s is outdated", self._cache_file)
        return False

    def get_cached_data(self):
        try:
            with self._cache_file.open(encoding="utf-8") as f:
                raw_content = f.read().strip()
        except FileNotFoundError:
            logging.info("No such file or directory %s (read from cache)", self._cache_file)
            raise
        except OSError as exc:
            logging.info("Cannot read from cache file: %s", exc)
            raise

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
        self._cache_file_dir.mkdir(parents=True, exist_ok=True)

        json_dump = json.dumps(raw_content, default=datetime_serializer)
        store.save_text_to_file(self._cache_file, json_dump)
