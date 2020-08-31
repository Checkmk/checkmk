#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from six import ensure_binary

from cmk.utils.type_defs import AgentRawData

from ._base import ABCFileCache, ABCFetcher


class AgentFileCache(ABCFileCache[AgentRawData]):
    pass


class DefaultAgentFileCache(AgentFileCache):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return raw_data

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
        return raw_data

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        return ensure_binary(raw_data)


class AgentFetcher(ABCFetcher[AgentRawData]):
    pass
