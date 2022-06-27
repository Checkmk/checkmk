#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import itertools
import json
import logging
from typing import Any, Final, List, Mapping, Optional, Sequence, Tuple

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.piggyback import get_piggyback_raw_data, PiggybackRawDataInfo, PiggybackTimeSettings
from cmk.utils.type_defs import AgentRawData, ExitSpec, HostAddress, HostName

from ._base import Fetcher, Summarizer
from .agent import AgentFileCache
from .type_defs import Mode


class PiggybackFetcher(Fetcher[AgentRawData]):
    def __init__(
        self,
        file_cache: AgentFileCache,
        *,
        hostname: HostName,
        address: Optional[HostAddress],
        time_settings: List[Tuple[Optional[str], str, int]],
    ) -> None:
        super().__init__(
            file_cache,
            logging.getLogger("cmk.helper.piggyback"),
        )
        self.hostname: Final = hostname
        self.address: Final = address
        self.time_settings: Final = time_settings
        self._sources: List[PiggybackRawDataInfo] = []

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"{type(self.file_cache).__name__}",
                    f"hostname={self.hostname!r}",
                    f"address={self.address!r}",
                    f"time_settings={self.time_settings!r}",
                )
            )
            + ")"
        )

    @classmethod
    def _from_json(cls, serialized: Mapping[str, Any]) -> "PiggybackFetcher":
        serialized_ = copy.deepcopy(dict(serialized))
        return cls(
            AgentFileCache.from_json(serialized_.pop("file_cache")),
            **serialized_,
        )

    def to_json(self) -> Mapping[str, Any]:
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

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        return AgentRawData(b"" + self._get_main_section() + self._get_source_labels_section())

    def _get_main_section(self) -> AgentRawData:
        raw_data = AgentRawData(b"")
        for src in self._sources:
            if src.info.successfully_processed:
                # !! Important for Check_MK and Check_MK Discovery service !!
                #   - sources contains ALL file infos and is not filtered
                #     in cmk/base/piggyback.py as in previous versions
                #   - Check_MK gets the processed file info reasons and displays them in
                #     it's service details
                #   - Check_MK Discovery: Only shows vanished/new/... if raw data is not
                #     added; ie. if file_info is not successfully processed
                raw_data = AgentRawData(raw_data + src.raw_data)
        return raw_data

    def _get_source_labels_section(self) -> AgentRawData:
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        if not self._sources:
            return AgentRawData(b"")

        labels = {
            "cmk/piggyback_source_%s" % src.info.source_hostname: "yes" for src in self._sources
        }
        return AgentRawData(b"<<<labels:sep(0)>>>\n%s\n" % json.dumps(labels).encode("utf-8"))

    @staticmethod
    def _raw_data(
        hostname: Optional[str],
        time_settings: PiggybackTimeSettings,
    ) -> Sequence[PiggybackRawDataInfo]:
        return get_piggyback_raw_data(hostname if hostname else "", time_settings)


class PiggybackSummarizer(Summarizer):
    def __init__(
        self,
        exit_spec: ExitSpec,
        *,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        time_settings: List[Tuple[Optional[str], str, int]],
        always: bool,
    ) -> None:
        super().__init__(exit_spec)
        self.hostname = hostname
        self.ipaddress = ipaddress
        self.time_settings = time_settings
        self.always = always

    def __repr__(self) -> str:
        return "%s(%r, hostname=%r, ipaddress=%r, time_settings=%r, always=%r)" % (
            type(self).__name__,
            self.exit_spec,
            self.hostname,
            self.ipaddress,
            self.time_settings,
            self.always,
        )

    def summarize_success(self) -> Sequence[ActiveCheckResult]:
        """Returns useful information about the data source execution"""

        sources: Final[Sequence[PiggybackRawDataInfo]] = list(
            itertools.chain.from_iterable(
                # TODO(ml): The code uses `get_piggyback_raw_data()` instead of
                # `HostSections.piggyback_raw_data` because this allows it to
                # sneakily use cached data.  At minimum, we should group all cache
                # handling performed after the parser.
                get_piggyback_raw_data(origin, self.time_settings)
                for origin in (self.hostname, self.ipaddress)
            )
        )
        if not sources:
            if self.always:
                return [ActiveCheckResult(1, "Missing data")]
            return []
        return [
            ActiveCheckResult(src.info.status, src.info.message)
            for src in sources
            if src.info.message
        ]
