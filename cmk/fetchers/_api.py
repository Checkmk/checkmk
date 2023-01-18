#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from functools import partial
from typing import Protocol

import cmk.utils.tty as tty
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.exceptions import MKFetcherError
from cmk.utils.log import console
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, result

from cmk.snmplib.type_defs import SNMPRawData, TRawData

from ._abstract import Fetcher, Mode
from ._typedefs import SourceInfo
from .filecache import FileCache

__all__ = ["get_raw_data", "fetch_all", "FetcherFunction"]


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


def fetch_all(
    sources: Iterable[tuple[SourceInfo, FileCache, Fetcher]],
    *,
    mode: Mode,
) -> Sequence[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]]:
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    return [
        do_fetch(source_info, file_cache, fetcher, mode=mode)
        for source_info, file_cache, fetcher in sources
    ]


def do_fetch(
    source_info: SourceInfo,
    file_cache: FileCache,
    fetcher: Fetcher,
    *,
    mode: Mode,
) -> tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]:
    console.vverbose(f"  Source: {source_info}\n")
    with CPUTracker() as tracker:
        raw_data = get_raw_data(file_cache, fetcher, mode)
    return source_info, raw_data, tracker.duration
