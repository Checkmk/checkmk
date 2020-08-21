#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple, Type

from cmk.utils.piggyback import get_piggyback_raw_data, PiggybackRawDataInfo, PiggybackTimeSettings
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName

from .agent import AgentFetcher, AgentFileCache


class PiggyBackFileCache(AgentFileCache):
    """Piggy back does not cache raw data.

    This class is a stub.

    """
    def read(self) -> None:
        return None

    def write(self, raw_data: AgentRawData) -> None:
        pass


class PiggyBackFetcher(AgentFetcher):
    def __init__(
        self,
        file_cache: PiggyBackFileCache,
        hostname: HostName,
        address: Optional[HostAddress],
        time_settings: List[Tuple[Optional[str], str, int]],
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.fetchers.piggyback"))
        self._hostname = hostname
        self._address = address
        self._time_settings = time_settings
        self._sources: List[PiggybackRawDataInfo] = []

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "PiggyBackFetcher":
        return cls(
            PiggyBackFileCache.from_json(serialized.pop("file_cache")),
            **serialized,
        )

    def __enter__(self) -> 'PiggyBackFetcher':
        for origin in (self._hostname, self._address):
            self._sources.extend(PiggyBackFetcher._raw_data(origin, self._time_settings))
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        self._sources.clear()

    def _fetch_from_io(self) -> AgentRawData:
        raw_data = b""
        raw_data += self._get_main_section()
        raw_data += self._get_source_labels_section()
        return raw_data

    def _get_main_section(self) -> AgentRawData:
        raw_data = b""
        for src in self._sources:
            if src.successfully_processed:
                # !! Important for Check_MK and Check_MK Discovery service !!
                #   - sources contains ALL file infos and is not filtered
                #     in cmk/base/piggyback.py as in previous versions
                #   - Check_MK gets the processed file info reasons and displays them in
                #     it's service details
                #   - Check_MK Discovery: Only shows vanished/new/... if raw data is not
                #     added; ie. if file_info is not successfully processed
                raw_data += src.raw_data
        return raw_data

    def _get_source_labels_section(self) -> AgentRawData:
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        if not self._sources:
            return b""

        labels = {"cmk/piggyback_source_%s" % src.source_hostname: "yes" for src in self._sources}
        return b'<<<labels:sep(0)>>>\n%s\n' % json.dumps(labels).encode("utf-8")

    @staticmethod
    def _raw_data(
        hostname: Optional[str],
        time_settings: PiggybackTimeSettings,
    ) -> List[PiggybackRawDataInfo]:
        return get_piggyback_raw_data(hostname if hostname else "", time_settings)
