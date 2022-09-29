#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, Literal, Mapping, Optional

import cmk.utils.paths
from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName, SectionName, SourceType

from cmk.snmplib.type_defs import SNMPHostConfig, SNMPRawData, SNMPRawDataSection

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType, SNMPFetcher
from cmk.core_helpers.cache import FileCacheGlobals, FileCacheMode, MaxAge, SectionStore
from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.snmp import SectionMeta, SNMPFileCache, SNMPParser, SNMPSummarizer

from ._abstract import Source


class SNMPSource(Source[SNMPRawData, SNMPRawDataSection]):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        source_type: SourceType,
        id_: Literal["snmp", "mgmt_snmp"],
        force_cache_refresh: bool,
        cache_dir: Optional[Path] = None,
        persisted_section_dir: Optional[Path] = None,
        title: str,
        on_scan_error: OnError,
        simulation_mode: bool,
        missing_sys_description: bool,
        sections: Mapping[SectionName, SectionMeta],
        check_intervals: Mapping[SectionName, Optional[int]],
        snmp_config: SNMPHostConfig,
        do_status_data_inventory: bool,
        file_cache_max_age: file_cache.MaxAge,
    ):
        super().__init__(
            hostname,
            ipaddress,
            source_type=source_type,
            fetcher_type=FetcherType.SNMP,
            description=SNMPSource._make_description(snmp_config, title=title),
            default_raw_data={},
            default_host_sections=HostSections[SNMPRawDataSection](),
            id_=id_,
            simulation_mode=simulation_mode,
            file_cache_max_age=file_cache_max_age,
        )
        self.snmp_config: Final = snmp_config
        self.missing_sys_description: Final = missing_sys_description
        self.sections: Final = sections
        self.check_intervals: Final = check_intervals
        self.do_status_data_inventory: Final = do_status_data_inventory
        self.on_snmp_scan_error: Final = on_scan_error
        self.force_cache_refresh: Final = force_cache_refresh
        if not persisted_section_dir:
            persisted_section_dir = Path(cmk.utils.paths.var_dir) / "persisted_sections" / self.id
        self.persisted_section_dir: Final[Path] = persisted_section_dir
        if not cache_dir:
            cache_dir = Path(cmk.utils.paths.data_source_cache_dir) / self.id
        self.file_cache_base_path: Final[Path] = cache_dir

    @classmethod
    def snmp(
        cls,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        id_: Literal["snmp"],
        on_scan_error: OnError,
        force_cache_refresh: bool,
        simulation_mode: bool,
        missing_sys_description: bool,
        sections: Mapping[SectionName, SectionMeta],
        check_intervals: Mapping[SectionName, Optional[int]],
        snmp_config: SNMPHostConfig,
        do_status_data_inventory: bool,
        file_cache_max_age: file_cache.MaxAge,
    ) -> "SNMPSource":
        return cls(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            id_=id_,
            title="SNMP",
            on_scan_error=on_scan_error,
            force_cache_refresh=force_cache_refresh,
            simulation_mode=simulation_mode,
            missing_sys_description=missing_sys_description,
            sections=sections,
            check_intervals=check_intervals,
            snmp_config=snmp_config,
            do_status_data_inventory=do_status_data_inventory,
            file_cache_max_age=file_cache_max_age,
        )

    @classmethod
    def management_board(
        cls,
        hostname: HostName,
        ipaddress: HostAddress,
        *,
        id_: Literal["mgmt_snmp"],
        on_scan_error: OnError,
        force_cache_refresh: bool,
        simulation_mode: bool,
        missing_sys_description: bool,
        sections: Mapping[SectionName, SectionMeta],
        check_intervals: Mapping[SectionName, Optional[int]],
        snmp_config: SNMPHostConfig,
        do_status_data_inventory: bool,
        file_cache_max_age: file_cache.MaxAge,
    ) -> "SNMPSource":
        return cls(
            hostname,
            ipaddress,
            source_type=SourceType.MANAGEMENT,
            id_=id_,
            title="Management board - SNMP",
            on_scan_error=on_scan_error,
            force_cache_refresh=force_cache_refresh,
            simulation_mode=simulation_mode,
            missing_sys_description=missing_sys_description,
            sections=sections,
            check_intervals=check_intervals,
            snmp_config=snmp_config,
            do_status_data_inventory=do_status_data_inventory,
            file_cache_max_age=file_cache_max_age,
        )

    def _make_file_cache(self) -> SNMPFileCache:
        return SNMPFileCache(
            self.hostname,
            base_path=self.file_cache_base_path,
            max_age=MaxAge.none() if self.force_cache_refresh else self.file_cache_max_age,
            use_outdated=self.simulation_mode
            or (False if self.force_cache_refresh else FileCacheGlobals.use_outdated),
            simulation=self.simulation_mode,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED
            if FileCacheGlobals.disabled
            else FileCacheMode.READ_WRITE,
        )

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
