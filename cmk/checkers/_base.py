#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from functools import partial
from typing import Generic

from cmk.utils.exceptions import MKFetcherError, MKIPAddressLookupError
from cmk.utils.type_defs import HostAddress, result

from cmk.snmplib.type_defs import TRawData

from cmk.fetchers import Fetcher, Mode

from .cache import FileCache
from .host_sections import HostSections, TRawDataSection
from .type_defs import SectionNameCollection

__all__ = ["verify_ipaddress", "get_raw_data"]


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


class Parser(Generic[TRawData, TRawDataSection], abc.ABC):
    """Parse raw data into host sections."""

    @abc.abstractmethod
    def parse(
        self, raw_data: TRawData, *, selection: SectionNameCollection
    ) -> HostSections[TRawDataSection]:
        raise NotImplementedError


def verify_ipaddress(address: HostAddress | None) -> None:
    if not address:
        raise MKIPAddressLookupError("Host has no IP address configured.")

    if address in ["0.0.0.0", "::"]:
        raise MKIPAddressLookupError(
            "Failed to lookup IP address and no explicit IP address configured"
        )
