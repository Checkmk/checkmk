#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any, Final

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.piggyback import get_piggyback_raw_data, PiggybackRawDataInfo, PiggybackTimeSettings

from cmk.fetchers import Fetcher, Mode


class PiggybackFetcher(Fetcher[AgentRawData]):
    def __init__(
        self,
        *,
        hostname: HostName,
        address: HostAddress | None,
        time_settings: Sequence[tuple[str | None, str, int]],
    ) -> None:
        super().__init__(logger=logging.getLogger("cmk.helper.piggyback"))
        self.hostname: Final = hostname
        self.address: Final = address
        self.time_settings: Final = time_settings
        self._sources: list[PiggybackRawDataInfo] = []

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"hostname={self.hostname!r}",
                    f"address={self.address!r}",
                    f"time_settings={self.time_settings!r}",
                )
            )
            + ")"
        )

    @classmethod
    def _from_json(cls, serialized: Mapping[str, Any]) -> "PiggybackFetcher":
        return cls(**copy.deepcopy(dict(serialized)))

    def to_json(self) -> Mapping[str, Any]:
        return {
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
        hostname: HostName | HostAddress | None,
        time_settings: PiggybackTimeSettings,
    ) -> Sequence[PiggybackRawDataInfo]:
        return get_piggyback_raw_data(hostname if hostname else HostName(""), time_settings)
