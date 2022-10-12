#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from typing import final, Final, Generic, Optional

from cmk.utils.type_defs import HostAddress, HostName, result, SourceType

from cmk.snmplib.type_defs import TRawData

from cmk.core_helpers import Fetcher, get_raw_data
from cmk.core_helpers.cache import FileCache
from cmk.core_helpers.controller import FetcherType
from cmk.core_helpers.host_sections import TRawDataSection
from cmk.core_helpers.type_defs import Mode

__all__ = ["Source"]


class Source(Generic[TRawData, TRawDataSection], abc.ABC):
    """Hold the configuration to fetchers and checkers.

    At best, this should only hold static data, that is, every
    attribute is final.

    """

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        source_type: SourceType,
        fetcher_type: FetcherType,
        id_: str,
    ) -> None:
        self.hostname: Final = hostname
        self.ipaddress: Final = ipaddress
        self.source_type: Final = source_type
        self.fetcher_type: Final = fetcher_type
        self.id: Final = id_

        self._logger: Final = logging.getLogger("cmk.base.data_source.%s" % id_)

    def __repr__(self) -> str:
        return "%s(%r, %r, id=%r)" % (
            type(self).__name__,
            self.hostname,
            self.ipaddress,
            self.id,
        )

    @property
    def fetcher_configuration(self):
        return self._make_fetcher().to_json()

    @property
    def file_cache_configuration(self):
        return self._make_file_cache().to_json()

    @final
    def fetch(self, mode: Mode) -> result.Result[TRawData, Exception]:
        return get_raw_data(self._make_file_cache(), self._make_fetcher(), mode)

    @abc.abstractmethod
    def _make_file_cache(self) -> FileCache[TRawData]:
        raise NotImplementedError

    @abc.abstractmethod
    def _make_fetcher(self) -> Fetcher:
        """Create a fetcher with this configuration."""
        raise NotImplementedError
