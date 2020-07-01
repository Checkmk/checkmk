#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from types import TracebackType
from typing import List, Optional, Tuple, Type

from cmk.utils.piggyback import (
    get_piggyback_raw_data,
    PiggybackRawDataInfo,
    PiggybackTimeSettings,
)
from cmk.utils.type_defs import HostAddress, HostName, RawAgentData, ServiceCheckResult

from ._base import AbstractDataFetcher


class PiggyBackDataFetcher(AbstractDataFetcher):
    def __init__(self, hostname: HostName, address: Optional[HostAddress],
                 time_settings: List[Tuple[Optional[str], str, int]]) -> None:
        super(PiggyBackDataFetcher, self).__init__()
        self._hostname = hostname
        self._address = address
        self._time_settings = time_settings
        self._logger = logging.getLogger("cmk.fetchers.piggyback")
        self._sources: List[PiggybackRawDataInfo] = []

    def __enter__(self) -> 'PiggyBackDataFetcher':
        for origin in (self._hostname, self._address):
            self._sources.extend(PiggyBackDataFetcher._raw_data(origin, self._time_settings))
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        self._sources.clear()

    def data(self) -> RawAgentData:
        raw_data = b""
        raw_data += self._get_main_section()
        raw_data += self._get_source_labels_section()
        return raw_data

    def summary(self) -> ServiceCheckResult:
        states = [0]
        infotexts = set()
        for src in self._sources:
            states.append(src.reason_status)
            infotexts.add(src.reason)
        return max(states), ", ".join(infotexts), []

    def _get_main_section(self) -> RawAgentData:
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

    def _get_source_labels_section(self) -> RawAgentData:
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        if not self._sources:
            return b""

        labels = {"cmk/piggyback_source_%s" % src.source_hostname: "yes" for src in self._sources}
        return b'<<<labels:sep(0)>>>\n%s\n' % json.dumps(labels).encode("utf-8")

    @staticmethod
    def _raw_data(hostname: Optional[str],
                  time_settings: PiggybackTimeSettings) -> List[PiggybackRawDataInfo]:
        return get_piggyback_raw_data(hostname if hostname else "", time_settings)
