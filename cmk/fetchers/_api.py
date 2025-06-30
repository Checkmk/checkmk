#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sized
from functools import partial
from typing import TypeVar

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import MKFetcherError, MKTimeout

from ._abstract import Fetcher, Mode
from .filecache import FileCache

__all__ = ["get_raw_data"]

_TRawData = TypeVar("_TRawData", bound=Sized)


def get_raw_data(
    file_cache: FileCache[_TRawData], fetcher: Fetcher[_TRawData], mode: Mode
) -> result.Result[_TRawData, Exception]:
    try:
        cached = file_cache.read(mode)
        if cached is not None:
            return result.OK(cached)

        if file_cache.simulation:
            raise MKFetcherError(f"{fetcher}: data unavailable in simulation mode")

        fetched: result.Result[_TRawData, Exception] = result.Error(MKFetcherError("unknown error"))
        with fetcher:
            fetched = fetcher.fetch(mode)
        fetched.map(partial(file_cache.write, mode=mode))
        return fetched

    except MKTimeout:
        raise

    except Exception as exc:
        return result.Error(exc)
