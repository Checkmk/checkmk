#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import enum
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, final, Literal, Self

import cmk.ccc.resulttype as result
from cmk.ccc.cpu_tracking import Snapshot
from cmk.ccc.exceptions import MKTimeout
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.helper_interface import AgentRawData, JsonSerializable, SourceInfo
from cmk.checkengine.snmplib import SNMPPluginStore, SNMPRawData

__all__ = ["FetcherFunction", "DeserializationContext"]


@dataclass(frozen=True)
class DeserializationContext:
    """Runtime dependencies needed to rebuild fetcher objects from JSON.

    These are *not* part of the serialized payload because they are host-independent
    (e.g. the SNMP plugin store) or not serializable / known only to the reading
    process (the base path).

    Use this context for reconstructing fetchers and wrapped objects in fetchers.
    """

    base_path: Path
    snmp_plugin_store: SNMPPluginStore
    # Used by MetricBackendFetcher. Injected by the reading process so that this
    # (community) module does not depend on the (non-free) telemetry package;
    # the callable itself resolves its telemetry import lazily, at fetch time.
    make_output: Callable[[Path, Sequence[str]], str]


class FetcherFunction(ABC):
    @abstractmethod
    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[
            SourceInfo,
            result.Result[AgentRawData | SNMPRawData, Exception],
            Snapshot,
        ]
    ]:
        raise NotImplementedError


class Mode(enum.Enum):
    CHECKING = enum.auto()
    DISCOVERY = enum.auto()
    INVENTORY = enum.auto()
    RTC = enum.auto()
    # Special case for discovery/checking/inventory command line argument where we specify in
    # advance all sections we want. Should disable caching, and in the SNMP case also detection.
    # Disabled sections must *not* be discarded in this mode.
    FORCE_SECTIONS = enum.auto()


class Fetcher[TRawData, TParams: Mapping[str, object] = Any](
    JsonSerializable[TParams, DeserializationContext], abc.ABC
):
    """Interface to the data fetchers.

    `TParams` is the concrete (`TypedDict`) shape of this fetcher's serialized
    params. Concrete fetchers bind it (e.g. `Fetcher[AgentRawData, TCPFetcherParams]`)
    to get strong typing on `serialized_params`/`from_params`.

    It is invariant (it appears in both the return of `serialized_params` and
    the parameter of `from_params`), so it defaults to `Any` rather than
    `Mapping[str, object]`: that keeps the many `Fetcher[SomeRawData]`
    annotations -- which don't care about the params shape -- compatible with
    every concrete fetcher, instead of only with an exact params match.
    """

    @final
    def __enter__(self) -> Self:
        return self

    @final
    def __exit__(self, *exc_info: object) -> Literal[False]:
        """Close the data source."""
        self.close()
        return False

    @abc.abstractmethod
    def open(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def close(self) -> None:
        raise NotImplementedError()

    @final
    def fetch(self, mode: Mode) -> result.Result[TRawData, Exception]:
        """Return the data from the source, either cached or from IO."""
        try:
            self.open()
            return result.OK(self._fetch_from_io(mode))
        except MKTimeout:
            raise
        except FetcherError:
            raise
        except Exception as exc:
            return result.Error(FetcherError(repr(exc) if any(exc.args) else type(exc).__name__))

    @abc.abstractmethod
    def _fetch_from_io(self, mode: Mode) -> TRawData:
        """Override this method to contact the source and return the raw data."""
        raise NotImplementedError()


class FetcherError(Exception):
    """An exception common to the fetchers."""
