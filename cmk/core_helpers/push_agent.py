#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from typing import Any, Final, Mapping

import cmk.utils.debug
from cmk.utils.exceptions import MKFetcherError
from cmk.utils.type_defs import AgentRawData
import cmk.utils.paths

from .agent import AgentFetcher, DefaultAgentFileCache
from .cache import FileCacheFactory, MaxAge
from .type_defs import Mode


class PushAgentFileCache(DefaultAgentFileCache):
    def write(self, raw_data: AgentRawData, mode) -> None:
        # we must not write to the cache, otherwise we update the mtime!
        return


class PushAgentFileCacheFactory(FileCacheFactory[AgentRawData]):
    # force_cache_refresh is currently only used by SNMP. It's probably less irritating
    # to implement it here anyway:
    def make(self, *, force_cache_refresh: bool = False) -> PushAgentFileCache:
        return PushAgentFileCache(
            self.hostname,
            base_path=self.base_path,
            max_age=MaxAge.none() if force_cache_refresh else self.max_age,
            disabled=self.disabled,
            use_outdated=False if force_cache_refresh else self.use_outdated,
            simulation=self.simulation,
        )


class PushAgentFetcher(AgentFetcher):
    def __init__(
        self,
        file_cache: PushAgentFileCache,
        *,
        allowed_age: int,
        use_only_cache: bool,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.helper.tcp"))
        self.allowed_age: Final = allowed_age
        self.use_only_cache: Final = use_only_cache

    def __repr__(self) -> str:
        return f"{type(self).__name__}(" + ", ".join((
            f"{type(self.file_cache).__name__}",
            f"allowed_age={self.allowed_age!r}",
            f"use_only_cache={self.use_only_cache!r}",
        )) + ")"

    @classmethod
    def _from_json(cls, serialized: Mapping[str, Any]) -> "PushAgentFetcher":
        return cls(
            PushAgentFileCache.from_json(serialized["file_cache"]),
            **{k: v for k, v in serialized.items() if k != "file_cache"},
        )

    def to_json(self) -> Mapping[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "allowed_age": self.allowed_age,
            "use_only_cache": self.use_only_cache,
        }

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        """
        The active agent cannot really 'fetch' live data.
        We consider data 'live', if they have been written to the cache
        by the receiver quite recently.
        """

        cache_file_path = self.file_cache.make_path(mode)

        try:
            if time.time() - cache_file_path.stat().st_mtime > self.allowed_age:
                raise MKFetcherError(f"No data received within the last {self.allowed_age}s")

            raw_data = cache_file_path.read_bytes()
        except FileNotFoundError as exc:
            if cmk.utils.debug.enabled():
                raise
            raise MKFetcherError("No data has been sent") from exc

        if len(raw_data) < 16:  # be consistent with TCPFetcher
            raise MKFetcherError("Received data set is too small")

        return AgentRawData(raw_data)
