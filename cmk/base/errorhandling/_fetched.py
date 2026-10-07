#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The fetched raw data as it is attached to crash reports"""

import datetime
from collections.abc import Iterable, Iterator, Sequence
from typing import override

import cmk.ccc.resulttype as result
import cmk.utils.paths
from cmk.ccc.cpu_tracking import Snapshot
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetcher_abc import FetcherFunction
from cmk.checkengine.helper_interface import AgentRawData, FetcherType, SourceInfo
from cmk.checkengine.snmplib import serialize_snmp_raw_data, SNMPRawData
from cmk.piggyback.backend import get_messages_for

type _Fetched = Sequence[
    tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
]


def serialize_fetched(
    fetched: Iterable[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]],
) -> AgentRawData | None:
    """Concatenate the raw data of all successfully fetched sources

    Each source is preceded by a separator line naming it, so that the
    output can be split into the individual sources again.
    SNMP data is serialized in the format of the SNMP file cache.
    The piggyback fetcher fetches nothing: the piggyback parser reads the
    stored piggyback messages. They are read here as well, each one
    preceded by a separator line naming its source host and last update.
    """
    chunks: list[bytes] = []
    for source, raw_data in fetched:
        if raw_data.is_error():
            continue
        header = f"===== {source.hostname} {source.ident} ({source.fetcher_type.name})"
        data = raw_data.ok
        payload = data if isinstance(data, bytes) else serialize_snmp_raw_data(data)
        chunks.extend(_chunk(f"{header} =====", payload))
        if source.fetcher_type is FetcherType.PIGGYBACK:
            for origin in (source.hostname, source.ipaddress):
                if origin is None:
                    continue
                for message in get_messages_for(origin, cmk.utils.paths.omd_root):
                    last_update = datetime.datetime.fromtimestamp(
                        message.meta.last_update, datetime.UTC
                    ).isoformat()
                    chunks.extend(
                        _chunk(
                            f"{header} from {message.meta.source}, last update {last_update} =====",
                            message.raw_data,
                        )
                    )
    return AgentRawData(b"".join(chunks)) if chunks else None


def _chunk(header: str, payload: bytes) -> Iterator[bytes]:
    yield f"{header}\n".encode()
    if payload:
        yield payload if payload.endswith(b"\n") else payload + b"\n"


class RecordingFetcher(FetcherFunction):
    """Remember what the wrapped fetcher returned for the most recent host"""

    def __init__(self, fetcher: FetcherFunction) -> None:
        self._fetcher = fetcher
        self._last: tuple[HostName, _Fetched] | None = None

    @override
    def __call__(self, host_name: HostName, *, ip_address: HostAddress | None) -> _Fetched:
        self._last = None
        fetched = self._fetcher(host_name, ip_address=ip_address)
        self._last = (host_name, fetched)
        return fetched

    def serialized(self, host_name: HostName) -> AgentRawData | None:
        """The serialized raw data of the most recent fetch, if it was for this host"""
        if self._last is None or self._last[0] != host_name:
            return None
        return serialize_fetched((f[0], f[1]) for f in self._last[1])
