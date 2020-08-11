#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from six import ensure_binary

from cmk.utils.type_defs import AgentRawData

from ._base import ABCFileCache, AbstractFetcher


class AgentFileCache(ABCFileCache[AgentRawData]):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return raw_data

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        raw_data = cast(AgentRawData, raw_data)
        # TODO: This does not seem to be needed
        return ensure_binary(raw_data)


class AgentFetcher(AbstractFetcher[AgentRawData]):
    pass
