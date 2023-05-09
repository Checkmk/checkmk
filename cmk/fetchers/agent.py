#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from six import ensure_binary

from cmk.utils.type_defs import AgentRawData

from ._base import ABCFetcher, ABCFileCache
from .type_defs import Mode


class AgentFileCache(ABCFileCache[AgentRawData]):
    pass


class DefaultAgentFileCache(AgentFileCache):
    @staticmethod
    def cache_read(mode: Mode) -> bool:
        return mode is not Mode.FORCE_SECTIONS

    @staticmethod
    def cache_write(mode: Mode) -> bool:
        return True

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        # TODO: This does not seem to be needed
        return ensure_binary(raw_data)

    def make_path(self, mode: Mode) -> Path:
        return self.base_path


class NoCache(AgentFileCache):
    """Noop cache for fetchers that do not cache."""
    @staticmethod
    def cache_read(mode: Mode) -> bool:
        return False

    @staticmethod
    def cache_write(mode: Mode) -> bool:
        return False

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        return ensure_binary(raw_data)

    def make_path(self, mode: Mode) -> Path:
        return Path(os.devnull)


class AgentFetcher(ABCFetcher[AgentRawData]):
    pass
