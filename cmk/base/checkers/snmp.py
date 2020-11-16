#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from functools import cached_property
from pathlib import Path
from typing import Final, Optional, Set

from cmk.utils.type_defs import HostAddress, HostName, SectionName, ServiceCheckResult, SourceType

from cmk.snmplib.type_defs import (
    BackendSNMPTree,
    SNMPDetectSpec,
    SNMPPersistedSections,
    SNMPRawData,
    SNMPSectionContent,
    SNMPSections,
)

from cmk.fetchers import FetcherType, SNMPFetcher
from cmk.fetchers.snmp import SNMPFileCache, SNMPPluginStore, SNMPPluginStoreItem

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_table as check_table
import cmk.base.config as config

from ._abstract import HostSections, Parser, Source, Summarizer, FileCacheFactory, Mode


def make_plugin_store() -> SNMPPluginStore:
    return SNMPPluginStore({
        s.name: SNMPPluginStoreItem(
            [BackendSNMPTree.from_frontend(base=t.base, oids=t.oids) for t in s.trees],
            SNMPDetectSpec(s.detect_spec)) for s in agent_based_register.iter_all_snmp_sections()
    })


class SNMPHostSections(HostSections[SNMPRawData, SNMPSections, SNMPPersistedSections,
                                    SNMPSectionContent]):
    pass


class SNMPFileCacheFactory(FileCacheFactory[SNMPRawData]):
    def make(self) -> SNMPFileCache:
        return SNMPFileCache(
            path=self.path,
            max_age=self.max_age,
            disabled=self.disabled | self.snmp_disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


class SNMPSource(Source[SNMPRawData, SNMPHostSections]):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: HostAddress,
        *,
        mode: Mode,
        source_type: SourceType,
        id_: str,
        cache_dir: Optional[Path] = None,
        persisted_section_dir: Optional[Path] = None,
        title: str,
        on_error: str = "raise",
    ):
        super().__init__(
            hostname,
            ipaddress,
            mode=mode,
            source_type=source_type,
            fetcher_type=FetcherType.SNMP,
            description=SNMPSource._make_description(hostname, ipaddress, title=title),
            default_raw_data={},
            default_host_sections=SNMPHostSections(),
            id_=id_,
            cache_dir=cache_dir,
            persisted_section_dir=persisted_section_dir,
        )
        if self.ipaddress is None:
            # snmp_config.ipaddress is not Optional.
            #
            # At least classic SNMP enforces that there is an address set,
            # Inline-SNMP has some lookup logic for some reason. We need
            # to find out whether or not we can really have None here.
            # Looks like it could be the case for cluster hosts which
            # don't have an IP address set.
            raise TypeError(self.ipaddress)
        self.snmp_config = (
            # Because of crap inheritance.
            self.host_config.snmp_config(self.ipaddress)
            if self.source_type is SourceType.HOST else self.host_config.management_snmp_config)
        self.on_snmp_scan_error = on_error
        # Attributes below are wrong
        self.use_snmpwalk_cache = True
        self.ignore_check_interval = False

    @classmethod
    def snmp(
        cls,
        hostname: HostName,
        ipaddress: HostAddress,
        *,
        mode: Mode,
    ) -> "SNMPSource":
        assert ipaddress is not None
        return cls(
            hostname,
            ipaddress,
            mode=mode,
            source_type=SourceType.HOST,
            id_="snmp",
            title="SNMP",
        )

    @classmethod
    def management_board(
        cls,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
    ) -> "SNMPSource":
        if ipaddress is None:
            raise TypeError(ipaddress)
        return cls(
            hostname,
            ipaddress,
            mode=mode,
            source_type=SourceType.MANAGEMENT,
            id_="mgmt_snmp",
            title="Management board - SNMP",
        )

    def _make_file_cache(self) -> SNMPFileCache:
        return SNMPFileCacheFactory(
            path=self.file_cache_path,
            simulation=config.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> SNMPFetcher:
        return SNMPFetcher(
            self._make_file_cache(),
            snmp_plugin_store=self._make_snmp_plugin_store(),
            disabled_sections=self._make_disabled_sections(),
            configured_snmp_sections=self._make_configured_snmp_sections(),
            inventory_snmp_sections=self._make_inventory_snmp_sections(),
            on_error=self.on_snmp_scan_error,
            missing_sys_description=config.get_config_cache().in_binary_hostlist(
                self.snmp_config.hostname,
                config.snmp_without_sys_descr,
            ),
            use_snmpwalk_cache=self.use_snmpwalk_cache,
            do_status_data_inventory=self.host_config.do_status_data_inventory,
            snmp_config=self.snmp_config,
        )

    def _make_parser(self) -> "SNMPParser":
        return SNMPParser(
            self.hostname,
            self.persisted_sections_file_path,
            self.use_outdated_persisted_sections,
            self._logger,
        )

    def _make_summarizer(self) -> "SNMPSummarizer":
        return SNMPSummarizer(self.exit_spec)

    @staticmethod
    def _make_snmp_plugin_store() -> SNMPPluginStore:
        return make_plugin_store()

    def _make_disabled_sections(self) -> Set[SectionName]:
        return self.host_config.disabled_snmp_sections()

    def _make_configured_snmp_sections(self) -> Set[SectionName]:
        return self._enabled_snmp_sections.intersection(
            agent_based_register.get_relevant_raw_sections(
                check_plugin_names=check_table.get_needed_check_names(
                    self.hostname,
                    filter_mode="include_clustered",
                    skip_ignored=True,
                ),
                consider_inventory_plugins=False,
            ))

    def _make_inventory_snmp_sections(self) -> Set[SectionName]:
        return self._enabled_snmp_sections.intersection(
            agent_based_register.get_relevant_raw_sections(
                check_plugin_names=(),
                consider_inventory_plugins=True,
            ))

    # TODO: filter out disabled sections in fetcher. They need to known them anyway.
    @cached_property
    def _enabled_snmp_sections(self) -> Set[SectionName]:
        return {s.name for s in agent_based_register.iter_all_snmp_sections()
               } - self.host_config.disabled_snmp_sections()

    @staticmethod
    def _make_description(
        hostname: HostName,
        ipaddress: HostAddress,
        *,
        title: str,
    ) -> str:
        snmp_config = config.HostConfig.make_snmp_config(hostname, ipaddress)
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


class SNMPParser(Parser[SNMPRawData, SNMPHostSections]):
    """A parser for SNMP data."""
    def __init__(
        self,
        hostname: HostName,
        persisted_sections_file_path: Path,
        use_outdated_persisted_sections: bool,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final[HostName] = hostname
        self.host_config = config.HostConfig.make_host_config(self.hostname)
        self.persisted_sections_file_path: Final[Path] = persisted_sections_file_path
        self.use_outdated_persisted_sections: Final[bool] = use_outdated_persisted_sections
        self._logger = logger

    def parse(
        self,
        raw_data: SNMPRawData,
    ) -> SNMPHostSections:
        persisted_sections = SNMPParser._extract_persisted_sections(
            raw_data,
            self.host_config,
        )
        host_sections = SNMPHostSections(raw_data, persisted_sections=persisted_sections)
        host_sections.add_persisted_sections(
            self.persisted_sections_file_path,
            self.use_outdated_persisted_sections,
            logger=self._logger,
        )
        return host_sections

    @staticmethod
    def _extract_persisted_sections(
        raw_data: SNMPRawData,
        host_config: config.HostConfig,
    ) -> SNMPPersistedSections:
        """Extract the sections to be persisted from the raw_data and return it

        Gather the check types to be persisted, extract the related data from
        the raw data, calculate the times and store the persisted info for
        later use.
        """
        persisted_sections: SNMPPersistedSections = {}

        for section_name, section_content in raw_data.items():
            fetch_interval = host_config.snmp_fetch_interval(section_name)
            if fetch_interval is None:
                continue

            cached_at = int(time.time())
            until = cached_at + (fetch_interval * 60)
            persisted_sections[section_name] = (cached_at, until, section_content)

        return persisted_sections


class SNMPSummarizer(Summarizer[SNMPHostSections]):
    def summarize_success(self, host_sections: SNMPHostSections) -> ServiceCheckResult:
        return 0, "Success", []
