#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from functools import partial
from typing import Protocol

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import MKFetcherError
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, result

from cmk.snmplib.type_defs import SNMPRawData, TRawData

from ._abstract import Fetcher, Mode
from ._typedefs import SourceInfo
from .filecache import FileCache

__all__ = ["get_raw_data", "FetcherFunction"]


class FetcherFunction(Protocol):
    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ]:
        ...


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
