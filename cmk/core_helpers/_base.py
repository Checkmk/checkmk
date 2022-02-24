#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from types import TracebackType
from typing import Any, final, Final, Generic, Literal, Mapping, Optional, Sequence, Type, TypeVar

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import (
    MKAgentError,
    MKEmptyAgentData,
    MKFetcherError,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTimeout,
)
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import ExitSpec, HostAddress, result

from cmk.snmplib.type_defs import TRawData

from .cache import FileCache
from .host_sections import HostSections, TRawDataSection
from .type_defs import Mode, SectionNameCollection

__all__ = ["Fetcher", "verify_ipaddress"]

TFetcher = TypeVar("TFetcher", bound="Fetcher")


class Fetcher(Generic[TRawData], abc.ABC):
    """Interface to the data fetchers."""

    def __init__(
        self,
        file_cache: FileCache,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.file_cache: Final[FileCache[TRawData]] = file_cache
        self._logger = logger

    @final
    @classmethod
    def from_json(cls: Type[TFetcher], serialized: Mapping[str, Any]) -> TFetcher:
        """Deserialize from JSON."""
        return cls._from_json(serialized)

    @classmethod
    @abc.abstractmethod
    def _from_json(cls: Type[TFetcher], serialized: Mapping[str, Any]) -> TFetcher:
        raise NotImplementedError()

    @abc.abstractmethod
    def to_json(self) -> Mapping[str, Any]:
        """Serialize to JSON."""
        raise NotImplementedError()

    @final
    def __enter__(self) -> "Fetcher":
        """Prepare the data source. Only needed if simulation mode is
        disabled"""
        if self.file_cache.simulation:
            return self

        try:
            self.open()
        except MKFetcherError:
            raise
        except Exception as exc:
            raise MKFetcherError(repr(exc) if any(exc.args) else type(exc).__name__) from exc
        return self

    @final
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Literal[False]:
        """Destroy the data source. Only needed if simulation mode is
        disabled"""
        if self.file_cache.simulation:
            return False
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
            return result.OK(self._fetch(mode))
        except Exception as exc:
            return result.Error(exc)

    def _fetch(self, mode: Mode) -> TRawData:
        self._logger.debug(
            "[%s] Fetch with cache settings: %r",
            self.__class__.__name__,
            self.file_cache,
        )
        raw_data = self.file_cache.read(mode)
        if raw_data:
            self._logger.log(VERBOSE, "[%s] Use cached data", self.__class__.__name__)
            return raw_data

        self._logger.log(VERBOSE, "[%s] Execute data source", self.__class__.__name__)
        raw_data = self._fetch_from_io(mode)
        self.file_cache.write(raw_data, mode)
        return raw_data

    @abc.abstractmethod
    def _fetch_from_io(self, mode: Mode) -> TRawData:
        """Override this method to contact the source and return the raw data."""
        raise NotImplementedError()


class Parser(Generic[TRawData, TRawDataSection], abc.ABC):
    """Parse raw data into host sections."""

    @abc.abstractmethod
    def parse(
        self, raw_data: TRawData, *, selection: SectionNameCollection
    ) -> HostSections[TRawDataSection]:
        raise NotImplementedError


class Summarizer(Generic[TRawDataSection], abc.ABC):
    """Class to summarize parsed data into a ServiceCheckResult.

    Note:
        It is forbidden to add base dependencies to classes
        that derive this class.

    """

    def __init__(self, exit_spec: ExitSpec) -> None:
        super().__init__()
        self.exit_spec: Final[ExitSpec] = exit_spec

    @abc.abstractmethod
    def summarize_success(
        self,
        host_sections: HostSections[TRawDataSection],
        *,
        mode: Mode,
    ) -> Sequence[ActiveCheckResult]:
        raise NotImplementedError

    def summarize_failure(
        self,
        exc: Exception,
        *,
        mode: Mode,
    ) -> Sequence[ActiveCheckResult]:
        return [ActiveCheckResult(self._extract_status(exc), str(exc))]

    def _extract_status(self, exc: Exception) -> int:
        if isinstance(exc, MKEmptyAgentData):
            return self.exit_spec.get("empty_output", 2)
        if isinstance(
            exc,
            (
                MKAgentError,
                MKFetcherError,
                MKIPAddressLookupError,
                MKSNMPError,
            ),
        ):
            return self.exit_spec.get("connection", 2)
        if isinstance(exc, MKTimeout):
            return self.exit_spec.get("timeout", 2)
        return self.exit_spec.get("exception", 3)


def verify_ipaddress(address: Optional[HostAddress]) -> None:
    if not address:
        raise MKIPAddressLookupError("Host has no IP address configured.")

    if address in ["0.0.0.0", "::"]:
        raise MKIPAddressLookupError(
            "Failed to lookup IP address and no explicit IP address configured"
        )
