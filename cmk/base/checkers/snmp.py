#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from pathlib import Path
from typing import Dict, Final, Optional, Set

from cmk.utils.type_defs import HostAddress, HostName, SectionName, ServiceCheckResult, SourceType

from cmk.snmplib.type_defs import BackendSNMPTree, SNMPDetectSpec, SNMPRawData, SNMPSectionContent

from cmk.fetchers import FetcherType, MaxAge, SNMPFetcher
from cmk.fetchers.cache import PersistedSections, SectionStore
from cmk.fetchers.snmp import SectionMeta, SNMPFileCache, SNMPPluginStore, SNMPPluginStoreItem

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_table as check_table
import cmk.base.config as config

from ._abstract import FileCacheFactory, Mode, Parser, Source, Summarizer
from .host_sections import HostSections
from .type_defs import NO_SELECTION, SectionNameCollection


def make_inventory_sections() -> Set[SectionName]:
    return {
        s for s in agent_based_register.get_relevant_raw_sections(
            check_plugin_names=(),
            inventory_plugin_names=(
                p.name for p in agent_based_register.iter_all_inventory_plugins()))
        if agent_based_register.is_registered_snmp_section_plugin(s)
    }


def make_plugin_store() -> SNMPPluginStore:
    inventory_sections = make_inventory_sections()
    return SNMPPluginStore({
        s.name: SNMPPluginStoreItem(
            [BackendSNMPTree.from_frontend(base=t.base, oids=t.oids) for t in s.trees],
            SNMPDetectSpec(s.detect_spec),
            s.name in inventory_sections,
        ) for s in agent_based_register.iter_all_snmp_sections()
    })


SNMPHostSections = HostSections[SNMPSectionContent]


class SNMPFileCacheFactory(FileCacheFactory[SNMPRawData]):
    def make(self) -> SNMPFileCache:
        return SNMPFileCache(
            base_path=self.base_path,
            max_age=MaxAge.none(),
            disabled=self.disabled,
            use_outdated=False,
            simulation=self.simulation,
        ) if self.force_snmp_cache_refresh else SNMPFileCache(
            base_path=self.base_path,
            max_age=self.max_age,
            disabled=self.disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


class SNMPSource(Source[SNMPRawData, SNMPHostSections]):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        source_type: SourceType,
        selected_sections: SectionNameCollection,
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
            description=SNMPSource._make_description(source_type, hostname, ipaddress, title=title),
            default_raw_data=SNMPRawData({}),
            default_host_sections=SNMPHostSections(),
            id_=id_,
            cache_dir=cache_dir,
            persisted_section_dir=persisted_section_dir,
        )
        self.selected_sections = selected_sections
        self.snmp_config = (
            # Because of crap inheritance.
            self.host_config.snmp_config(self.ipaddress)
            if self.source_type is SourceType.HOST else self.host_config.management_snmp_config)
        self.on_snmp_scan_error = on_error

    @classmethod
    def snmp(
        cls,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        selected_sections: SectionNameCollection,
    ) -> "SNMPSource":
        return cls(
            hostname,
            ipaddress,
            mode=mode,
            source_type=SourceType.HOST,
            selected_sections=selected_sections,
            id_="snmp",
            title="SNMP",
        )

    @classmethod
    def management_board(
        cls,
        hostname: HostName,
        ipaddress: HostAddress,
        *,
        mode: Mode,
        selected_sections: SectionNameCollection,
    ) -> "SNMPSource":
        return cls(
            hostname,
            ipaddress,
            mode=mode,
            source_type=SourceType.MANAGEMENT,
            selected_sections=selected_sections,
            id_="mgmt_snmp",
            title="Management board - SNMP",
        )

    def _make_file_cache(self) -> SNMPFileCache:
        return SNMPFileCacheFactory(
            base_path=self.file_cache_base_path,
            simulation=config.simulation_mode,
            max_age=self.file_cache_max_age,
        ).make()

    def _make_fetcher(self) -> SNMPFetcher:
        if len(SNMPFetcher.plugin_store) != agent_based_register.len_snmp_sections():
            # That's a hack.
            #
            # `make_plugin_store()` depends on
            # `iter_all_snmp_sections()` and `iter_all_inventory_plugins()`
            # that are populated by the Check API upon loading the plugins.
            #
            # It is there, when the plugins are loaded, that we should
            # make the plugin store.  However, it is not clear whether
            # the API would let us register hooks to accomplish that.
            #
            # The current solution is brittle in that there is not guarantee
            # that all the relevant plugins are loaded at this point.
            SNMPFetcher.plugin_store = make_plugin_store()
        return SNMPFetcher(
            self._make_file_cache(),
            sections=self._make_sections(),
            on_error=self.on_snmp_scan_error,
            missing_sys_description=config.get_config_cache().in_binary_hostlist(
                self.snmp_config.hostname,
                config.snmp_without_sys_descr,
            ),
            do_status_data_inventory=self.host_config.do_status_data_inventory,
            section_store_path=self.persisted_sections_file_path,
            snmp_config=self.snmp_config,
        )

    def _make_sections(self) -> Dict[SectionName, SectionMeta]:
        checking_sections = self._make_checking_sections()
        disabled_sections = self._make_disabled_sections()
        return {
            name: SectionMeta(
                checking=name in checking_sections,
                disabled=name in disabled_sections,
                redetect=name in checking_sections and self._needs_redetection(name),
                fetch_interval=self.host_config.snmp_fetch_interval(name),
            ) for name in (checking_sections | disabled_sections)
        }

    def _make_parser(self) -> "SNMPParser":
        return SNMPParser(
            self.hostname,
            SectionStore[SNMPSectionContent](
                self.persisted_sections_file_path,
                keep_outdated=self.use_outdated_persisted_sections,
                logger=self._logger,
            ),
            self._logger,
        )

    def _make_summarizer(self) -> "SNMPSummarizer":
        return SNMPSummarizer(self.exit_spec)

    def _make_disabled_sections(self) -> Set[SectionName]:
        return self.host_config.disabled_snmp_sections()

    def _make_checking_sections(self) -> Set[SectionName]:
        if self.selected_sections is not NO_SELECTION:
            checking_sections = self.selected_sections
        else:
            checking_sections = set(
                agent_based_register.get_relevant_raw_sections(
                    check_plugin_names=check_table.get_needed_check_names(
                        self.hostname,
                        filter_mode="include_clustered",
                        skip_ignored=True,
                    ),
                    inventory_plugin_names=()))
        return {
            s for s in checking_sections
            if agent_based_register.is_registered_snmp_section_plugin(s)
        }

    @staticmethod
    def _needs_redetection(section_name: SectionName) -> bool:
        section = agent_based_register.get_section_plugin(section_name)
        return len(agent_based_register.get_section_producers(section.parsed_section_name)) > 1

    @staticmethod
    def _make_description(
        source_type: SourceType,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        title: str,
    ) -> str:
        host_config = config.get_config_cache().get_host_config(hostname)
        snmp_config = (host_config.snmp_config(ipaddress)
                       if source_type is SourceType.HOST else host_config.management_snmp_config)

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
        section_store: SectionStore[SNMPSectionContent],
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.host_config: Final = config.HostConfig.make_host_config(self.hostname)
        self.section_store: Final = section_store
        self._logger = logger

    def parse(
        self,
        raw_data: SNMPRawData,
        *,
        selection: SectionNameCollection,
    ) -> SNMPHostSections:
        persisted_sections = SNMPParser._extract_persisted_sections(
            raw_data,
            self.host_config,
        )
        self.section_store.update(persisted_sections)
        host_sections = SNMPHostSections(dict(raw_data))
        host_sections.add_persisted_sections(
            persisted_sections,
            logger=self._logger,
        )
        return host_sections

    @staticmethod
    def _extract_persisted_sections(
        raw_data: SNMPRawData,
        host_config: config.HostConfig,
    ) -> PersistedSections[SNMPSectionContent]:
        """Extract the sections to be persisted from the raw_data and return it

        Gather the check types to be persisted, extract the related data from
        the raw data, calculate the times and store the persisted info for
        later use.
        """
        persisted_sections = PersistedSections[SNMPSectionContent]({})

        for section_name, section_content in raw_data.items():
            fetch_interval = host_config.snmp_fetch_interval(section_name)
            if fetch_interval is None:
                continue

            cached_at = int(time.time())
            until = cached_at + (fetch_interval * 60)
            # pylint does not seem to understand `NewType`... leave the checking up to mypy.
            persisted_sections[section_name] = (  # false positive: pylint: disable=E1137
                (cached_at, until, section_content))

        return persisted_sections


class SNMPSummarizer(Summarizer[SNMPHostSections]):
    def summarize_success(self, host_sections: SNMPHostSections) -> ServiceCheckResult:
        return 0, "Success", []
