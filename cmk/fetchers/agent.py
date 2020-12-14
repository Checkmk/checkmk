#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from six import ensure_binary

from cmk.utils.type_defs import AgentRawData

from .cache import FileCache, FileCacheFactory
from ._base import Fetcher


class AgentFileCache(FileCache[AgentRawData]):
    pass


class DefaultAgentFileCache(AgentFileCache):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        # TODO: This does not seem to be needed
        return ensure_binary(raw_data)


class NoCache(AgentFileCache):
    """Noop cache for fetchers that do not cache."""
    def read(self) -> None:
        return None

    def write(self, raw_data: AgentRawData) -> None:
        pass

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        return ensure_binary(raw_data)


class DefaultAgentFileCacheFactory(FileCacheFactory[AgentRawData]):
    def make(self) -> DefaultAgentFileCache:
        return DefaultAgentFileCache(
            path=self.path,
            max_age=self.max_age,
            disabled=self.disabled | self.agent_disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


class NoCacheFactory(FileCacheFactory[AgentRawData]):
    def make(self) -> NoCache:
        return NoCache(
            path=self.path,
            max_age=self.max_age,
            disabled=self.disabled | self.agent_disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


class AgentFetcher(Fetcher[AgentRawData]):
    pass
