#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from cmk.utils.agentdatatype import AgentRawData

from ._cache import FileCache

__all__ = ["AgentFileCache"]


class AgentFileCache(FileCache[AgentRawData]):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        return raw_data
