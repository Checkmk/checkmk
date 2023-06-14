#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial

import cmk.utils.resulttype as result
from cmk.utils.exceptions import MKFetcherError

from cmk.snmplib.type_defs import TRawData

from ._abstract import Fetcher, Mode
from .filecache import FileCache

__all__ = ["get_raw_data"]


def get_raw_data(
    file_cache: FileCache[TRawData], fetcher: Fetcher[TRawData], mode: Mode
) -> result.Result[TRawData, Exception]:
    try:
        cached = file_cache.read(mode)
        if cached is not None:
            return result.OK(cached)

        if file_cache.simulation:
            raise MKFetcherError(f"{fetcher}: data unavailable in simulation mode")

        fetched: result.Result[TRawData, Exception] = result.Error(
            MKFetcherError(f"{fetcher}: unknown error")
        )
        with fetcher:
            fetched = fetcher.fetch(mode)
        fetched.map(partial(file_cache.write, mode=mode))
        return fetched

    except Exception as exc:
        return result.Error(exc)
