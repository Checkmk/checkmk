#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from collections.abc import Sequence
from typing import Final

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.log import VERBOSE
from cmk.utils.piggyback import get_piggyback_raw_data, PiggybackRawDataInfo, PiggybackTimeSettings

from ._abstract import Fetcher, Mode


class PiggybackFetcher(Fetcher[AgentRawData]):
    def __init__(
        self,
        *,
        hostname: HostName,
        address: HostAddress | None,
        time_settings: Sequence[tuple[str | None, str, int]],
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.address: Final = address
        self.time_settings: Final = time_settings
        self._logger: Final = logging.getLogger("cmk.helper.piggyback")
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PiggybackFetcher):
            return False
        return (
            self.hostname == other.hostname
            and self.address == other.address
            and self.time_settings == other.time_settings
        )

    def open(self) -> None:
        for origin in (self.hostname, self.address):
            self._sources.extend(PiggybackFetcher._raw_data(origin, self.time_settings))

    def close(self) -> None:
        self._sources.clear()

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        self._logger.log(VERBOSE, "Get piggybacked data")
        return AgentRawData(
            bytes(
                self._get_main_section()
                + self._get_source_summary_section()
                + self._get_source_labels_section()
            )
        )

    def _get_main_section(self) -> bytearray | bytes:
        raw_data = bytearray()
        for src in self._sources:
            if src.info.valid:
                # !! Important for Check_MK and Check_MK Discovery service !!
                #   - sources contains ALL file infos and is not filtered
                #     in cmk/base/piggyback.py as in previous versions
                #   - Check_MK gets the processed file info reasons and displays them in
                #     it's service details
                #   - Check_MK Discovery: Only shows vanished/new/... if raw data is not
                #     added; ie. if file_info is not successfully processed
                raw_data += src.raw_data
        return raw_data

    def _get_source_summary_section(self) -> bytes:
        """Add some meta information about the piggyback sources to the agent output.

        The fetcher messages currently lack the capability to add additional meta information
        to the sources (other than one single exception).
        Since we're adding payload anyway, we add this section as well, to be consumed by the summarizer.
        """
        return f"<<<piggyback_source_summary:sep(0)>>>\n{'\n'.join(s.info.serialize() for s in self._sources)}\n".encode(
            "utf-8"
        )

    def _get_source_labels_section(self) -> bytearray | bytes:
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        if not self._sources:
            return b""

        labels = {"cmk/piggyback_source_%s" % src.info.source: "yes" for src in self._sources}
        return ("<<<labels:sep(0)>>>\n%s\n" % json.dumps(labels)).encode("utf-8")

    @staticmethod
    def _raw_data(
        hostname: HostName | HostAddress | None,
        time_settings: PiggybackTimeSettings,
    ) -> Sequence[PiggybackRawDataInfo]:
        return get_piggyback_raw_data(hostname if hostname else HostName(""), time_settings)
