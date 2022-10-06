#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Literal, Mapping, Optional

from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, SectionName, SourceType

from cmk.snmplib.type_defs import SNMPHostConfig, SNMPRawData, SNMPRawDataSection

from cmk.core_helpers import FetcherType, SNMPFetcher
from cmk.core_helpers.cache import FileCache, SectionStore
from cmk.core_helpers.snmp import SectionMeta, SNMPParser, SNMPSummarizer

from ._abstract import Source


class SNMPSource(Source[SNMPRawData, SNMPRawDataSection]):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        source_type: SourceType,
        fetcher_type: FetcherType,
        id_: Literal["snmp", "mgmt_snmp"],
        persisted_section_dir: Path,
        on_scan_error: OnError,
        missing_sys_description: bool,
        sections: Mapping[SectionName, SectionMeta],
        keep_outdated: bool,
        check_intervals: Mapping[SectionName, Optional[int]],
        snmp_config: SNMPHostConfig,
        do_status_data_inventory: bool,
        cache: FileCache[SNMPRawData],
    ):
        super().__init__(
            hostname,
            ipaddress,
            source_type=source_type,
            fetcher_type=fetcher_type,
            id_=id_,
        )
        self.snmp_config: Final = snmp_config
        self.missing_sys_description: Final = missing_sys_description
        self.sections: Final = sections
        self.keep_outdated: Final = keep_outdated
        self.check_intervals: Final = check_intervals
        self.do_status_data_inventory: Final = do_status_data_inventory
        self.on_snmp_scan_error: Final = on_scan_error
        self.persisted_section_dir: Final = persisted_section_dir
        self.cache: Final = cache

    def _make_file_cache(self) -> FileCache[SNMPRawData]:
        return self.cache

    def _make_fetcher(self) -> SNMPFetcher:
        return SNMPFetcher(
            sections=self.sections,
            on_error=self.on_snmp_scan_error,
            missing_sys_description=self.missing_sys_description,
            do_status_data_inventory=self.do_status_data_inventory,
            section_store_path=self.persisted_section_dir / self.hostname,
            snmp_config=self.snmp_config,
        )

    def _make_parser(self) -> SNMPParser:
        return SNMPParser(
            self.hostname,
            SectionStore[SNMPRawDataSection](
                self.persisted_section_dir / self.hostname,
                logger=self._logger,
            ),
            check_intervals=self.check_intervals,
            keep_outdated=self.keep_outdated,
            logger=self._logger,
        )

    def _make_summarizer(self, *, exit_spec: ExitSpec) -> SNMPSummarizer:
        return SNMPSummarizer(exit_spec)
