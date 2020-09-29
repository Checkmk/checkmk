#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from typing import Any, Dict, Final, List, Optional, Tuple

from cmk.utils.piggyback import get_piggyback_raw_data, PiggybackRawDataInfo, PiggybackTimeSettings
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName

from .agent import AgentFetcher, NoCache
from .type_defs import Mode


class PiggybackFetcher(AgentFetcher):
    def __init__(
        self,
        file_cache: NoCache,
        *,
        hostname: HostName,
        address: Optional[HostAddress],
        time_settings: List[Tuple[Optional[str], str, int]],
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.fetchers.piggyback"))
        self.hostname: Final = hostname
        self.address: Final = address
        self.time_settings: Final = time_settings
        self._sources: List[PiggybackRawDataInfo] = []

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "PiggybackFetcher":
        return cls(
            NoCache.from_json(serialized.pop("file_cache")),
            **serialized,
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "hostname": self.hostname,
            "address": self.address,
            "time_settings": self.time_settings,
        }

    def open(self) -> None:
        for origin in (self.hostname, self.address):
            self._sources.extend(PiggybackFetcher._raw_data(origin, self.time_settings))

    def close(self) -> None:
        self._sources.clear()

    def _is_cache_enabled(self, mode: Mode) -> bool:
        return mode is not Mode.CHECKING

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
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
