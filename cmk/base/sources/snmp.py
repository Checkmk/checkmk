#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Mapping, Optional

from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import ExitSpec, HostAddress, SectionName, SourceType

from cmk.snmplib.type_defs import SNMPHostConfig, SNMPRawData, SNMPRawDataSection

from cmk.core_helpers import FetcherType, SNMPFetcher
from cmk.core_helpers.cache import FileCache, SectionStore
from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.snmp import SectionMeta, SNMPFileCacheFactory, SNMPParser, SNMPSummarizer

from cmk.base.config import HostConfig

from ._abstract import Source


class SNMPSource(Source[SNMPRawData, SNMPRawDataSection]):
    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        source_type: SourceType,
        id_: str,
        force_cache_refresh: bool,
        cache_dir: Optional[Path] = None,
        persisted_section_dir: Optional[Path] = None,
        title: str,
        on_scan_error: OnError,
        simulation_mode: bool,
        missing_sys_description: bool,
        sections: Mapping[SectionName, SectionMeta],
        check_intervals: Mapping[SectionName, Optional[int]],
    ):
        snmp_config = (
            # Because of crap inheritance.
            host_config.snmp_config(ipaddress)
            if source_type is SourceType.HOST
            else host_config.management_snmp_config
        )
        super().__init__(
            host_config.hostname,
            ipaddress,
            source_type=source_type,
            fetcher_type=FetcherType.SNMP,
            description=SNMPSource._make_description(snmp_config, title=title),
            default_raw_data={},
            default_host_sections=HostSections[SNMPRawDataSection](),
            id_=id_,
            cache_dir=cache_dir,
            persisted_section_dir=persisted_section_dir,
            simulation_mode=simulation_mode,
        )
        self.host_config: Final = host_config
        self.snmp_config: Final = snmp_config
        self.missing_sys_description: Final = missing_sys_description
        self.sections: Final = sections
        self.check_intervals: Final = check_intervals
        self._on_snmp_scan_error: Final = on_scan_error
        self._force_cache_refresh: Final = force_cache_refresh

    @classmethod
    def snmp(
        cls,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        on_scan_error: OnError,
        force_cache_refresh: bool,
        simulation_mode: bool,
        missing_sys_description: bool,
        sections: Mapping[SectionName, SectionMeta],
        check_intervals: Mapping[SectionName, Optional[int]],
    ) -> "SNMPSource":
        return cls(
            host_config,
            ipaddress,
            source_type=SourceType.HOST,
            id_="snmp",
            title="SNMP",
            on_scan_error=on_scan_error,
            force_cache_refresh=force_cache_refresh,
            simulation_mode=simulation_mode,
            missing_sys_description=missing_sys_description,
            sections=sections,
            check_intervals=check_intervals,
        )

    @classmethod
    def management_board(
        cls,
        host_config: HostConfig,
        ipaddress: HostAddress,
        *,
        on_scan_error: OnError,
        force_cache_refresh: bool,
        simulation_mode: bool,
        missing_sys_description: bool,
        sections: Mapping[SectionName, SectionMeta],
        check_intervals: Mapping[SectionName, Optional[int]],
    ) -> "SNMPSource":
        return cls(
            host_config,
            ipaddress,
            source_type=SourceType.MANAGEMENT,
            id_="mgmt_snmp",
            title="Management board - SNMP",
            on_scan_error=on_scan_error,
            force_cache_refresh=force_cache_refresh,
            simulation_mode=simulation_mode,
            missing_sys_description=missing_sys_description,
            sections=sections,
            check_intervals=check_intervals,
        )

    def _make_file_cache(self) -> FileCache[SNMPRawData]:
        return SNMPFileCacheFactory(
            self.hostname,
            base_path=self.file_cache_base_path,
            simulation=self.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make(force_cache_refresh=self._force_cache_refresh)

    def _make_fetcher(self) -> SNMPFetcher:
        return SNMPFetcher(
            sections=self.sections,
            on_error=self._on_snmp_scan_error,
            missing_sys_description=self.missing_sys_description,
            do_status_data_inventory=self.host_config.do_status_data_inventory,
            section_store_path=self.persisted_sections_file_path,
            snmp_config=self.snmp_config,
        )

    def _make_parser(self) -> SNMPParser:
        return SNMPParser(
            self.hostname,
            SectionStore[SNMPRawDataSection](
                self.persisted_sections_file_path,
                logger=self._logger,
            ),
            check_intervals=self.check_intervals,
            keep_outdated=self.use_outdated_persisted_sections,
            logger=self._logger,
        )

    def _make_summarizer(self, *, exit_spec: ExitSpec) -> SNMPSummarizer:
        return SNMPSummarizer(exit_spec)

    @staticmethod
    def _make_description(
        snmp_config: SNMPHostConfig,
        *,
        title: str,
    ) -> str:
        if snmp_config.is_usewalk_host:
            return "SNMP (use stored walk)"

        if snmp_config.is_snmpv3_host:
            credentials_text = "Credentials: '%s'" % ", ".join(snmp_config.credentials)
        else:
            credentials_text = "Community: %r" % snmp_config.credentials

        if snmp_config.is_snmpv3_host or snmp_config.is_bulkwalk_host:
            bulk = "yes"
        else:
            bulk = "no"

        return "%s (%s, Bulk walk: %s, Port: %d, Backend: %s)" % (
            title,
            credentials_text,
            bulk,
            snmp_config.port,
            snmp_config.snmp_backend.value,
        )
