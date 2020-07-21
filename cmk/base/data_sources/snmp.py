#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import time
from typing import cast, Dict, Final, Iterable, List, Optional, Set

from cmk.utils.type_defs import HostAddress, HostName, SectionName, ServiceCheckResult, SourceType

from cmk.snmplib.snmp_scan import gather_available_raw_section_names, SNMPScanSection
from cmk.snmplib.type_defs import (
    SNMPHostConfig,
    SNMPPersistedSections,
    SNMPRawData,
    SNMPSectionContent,
    SNMPSections,
    SNMPTree,
)

from cmk.fetchers import factory, SNMPDataFetcher

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin
from cmk.base.check_utils import PiggybackRawData, SectionCacheInfo
from cmk.base.config import SelectedRawSections
from cmk.base.exceptions import MKAgentError

from ._abstract import ABCConfigurator, ABCDataSource, ABCHostSections


class SNMPHostSections(ABCHostSections[SNMPRawData, SNMPSections, SNMPPersistedSections,
                                       SNMPSectionContent]):
    def __init__(
        self,
        sections: Optional[SNMPSections] = None,
        cache_info: Optional[SectionCacheInfo] = None,
        piggybacked_raw_data: Optional[PiggybackRawData] = None,
        persisted_sections: Optional[SNMPPersistedSections] = None,
    ) -> None:
        super(SNMPHostSections, self).__init__(
            sections=sections if sections is not None else {},
            cache_info=cache_info if cache_info is not None else {},
            piggybacked_raw_data=piggybacked_raw_data if piggybacked_raw_data is not None else {},
            persisted_sections=persisted_sections if persisted_sections is not None else {},
        )

    def _extend_section(self, section_name: SectionName,
                        section_content: SNMPSectionContent) -> None:
        self.sections.setdefault(section_name, []).extend(section_content)  # type: ignore


class CachedSNMPDetector:
    """Object to run/cache SNMP detection"""
    def __init__(
        self,
        *,
        on_error: str = "raise",
        do_snmp_scan: bool = False,
    ) -> None:
        super(CachedSNMPDetector, self).__init__()
        # Optional set: None: we never tried, empty: we tried, but found nothing
        # TODO: Check if do_snmp_scan and on_error can be dropped.
        self.on_error = on_error
        self.do_snmp_scan = do_snmp_scan
        self._cached_result: Optional[Set[SectionName]] = None

    def sections(self) -> Iterable[SNMPScanSection]:
        return [
            SNMPScanSection(section.name, section.detect_spec)
            for section in agent_based_register.iter_all_snmp_sections()
        ]

    # TODO (mo): Make this (and the called) function(s) return the sections directly!
    def __call__(
        self,
        snmp_config: SNMPHostConfig,
    ) -> Set[SectionName]:
        """Returns a list of raw sections that shall be processed by this source.

        The logic is only processed once. Once processed, the answer is cached.
        """
        if self._cached_result is not None:
            return self._cached_result

        self._cached_result = gather_available_raw_section_names(
            self.sections(),
            on_error=self.on_error,
            do_snmp_scan=self.do_snmp_scan,
            binary_host=config.get_config_cache().in_binary_hostlist(
                snmp_config.hostname,
                config.snmp_without_sys_descr,
            ),
            backend=factory.backend(snmp_config),
        )
        return self._cached_result


class SNMPConfigurator(ABCConfigurator):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: HostAddress,
        *,
        source_type: SourceType,
        id_: str,
        cpu_tracking_id: str,
        title: str,
    ):
        super().__init__(
            hostname,
            ipaddress,
            source_type=source_type,
            description=SNMPConfigurator._make_description(hostname, ipaddress, title=title),
            id_=id_,
            cpu_tracking_id=cpu_tracking_id,
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

    @classmethod
    def snmp(
        cls,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
    ) -> "SNMPConfigurator":
        if ipaddress is None:
            raise TypeError(ipaddress)
        return cls(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            id_="snmp",
            cpu_tracking_id="snmp",
            title="SNMP",
        )

    @classmethod
    def management_board(
        cls,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
    ) -> "SNMPConfigurator":
        if ipaddress is None:
            raise TypeError(ipaddress)
        return cls(
            hostname,
            ipaddress,
            source_type=SourceType.MANAGEMENT,
            id_="mgmt_snmp",
            cpu_tracking_id="snmp",
            title="Management board - SNMP",
        )

    def configure_fetcher(self):
        raise NotImplementedError

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

        if snmp_config.is_inline_snmp_host:
            inline = "yes"
        else:
            inline = "no"

        if snmp_config.is_snmpv3_host:
            credentials_text = "Credentials: '%s'" % ", ".join(snmp_config.credentials)
        else:
            credentials_text = "Community: %r" % snmp_config.credentials

        if snmp_config.is_snmpv3_host or snmp_config.is_bulkwalk_host:
            bulk = "yes"
        else:
            bulk = "no"

        return "%s (%s, Bulk walk: %s, Port: %d, Inline: %s)" % (
            title,
            credentials_text,
            bulk,
            snmp_config.port,
            inline,
        )


class SNMPDataSource(ABCDataSource[SNMPRawData, SNMPSections, SNMPPersistedSections,
                                   SNMPHostSections]):
    def __init__(self, *, configurator: SNMPConfigurator) -> None:
        super(SNMPDataSource, self).__init__(configurator=configurator)
        self.detector: Final = CachedSNMPDetector()
        self._use_snmpwalk_cache = True
        self._ignore_check_interval = False
        self._fetched_raw_section_names: Set[SectionName] = set()

    def _cache_dir(self) -> str:  # pylint: disable=useless-super-delegation
        return super()._cache_dir()

    def _persisted_sections_dir(self) -> str:  # pylint: disable=useless-super-delegation
        return super()._persisted_sections_dir()

    def _summary_result(self, for_checking: bool) -> ServiceCheckResult:
        return 0, "Success", []

    def _empty_raw_data(self) -> SNMPRawData:
        return {}

    def _empty_host_sections(self) -> SNMPHostSections:
        return SNMPHostSections()

    def _from_cache_file(self, raw_data: bytes) -> SNMPRawData:
        return {SectionName(k): v for k, v in ast.literal_eval(raw_data.decode("utf-8")).items()}

    def _to_cache_file(self, raw_data: SNMPRawData) -> bytes:
        return (repr({str(k): v for k, v in raw_data.items()}) + "\n").encode("utf-8")

    def set_ignore_check_interval(self, ignore_check_interval: bool) -> None:
        self._ignore_check_interval = ignore_check_interval

    def set_use_snmpwalk_cache(self, use_snmpwalk_cache: bool) -> None:
        self._use_snmpwalk_cache = use_snmpwalk_cache

    def set_fetched_raw_section_names(self, raw_section_names: Set[SectionName]) -> None:
        """Sets a list of already fetched host sections/check plugin names.

        Especially for SNMP data sources there are already fetched
        host sections of executed check plugins. But for some inventory plugins
        which have no related check plugin the host must be contacted again
        in order to create the full tree.
        """
        self._fetched_raw_section_names = raw_section_names

    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> SNMPRawData:
        ip_lookup.verify_ipaddress(self.configurator.ipaddress)
        with SNMPDataFetcher(
                self._make_oid_infos(selected_raw_sections=selected_raw_sections),
                self._use_snmpwalk_cache,
                # TODO(ml): cast: this has to move to the configurator anyway.
                cast(SNMPConfigurator, self.configurator).snmp_config,
        ) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    def _make_oid_infos(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> Dict[SectionName, List[SNMPTree]]:
        oid_infos = {}  # Dict[SectionName, List[SNMPTree]]
        # TODO(ml): This should move to the Configurator as well.
        configurator = cast(SNMPConfigurator, self.configurator)
        for section_name in SNMPDataSource._sort_section_names(
            {s.name for s in selected_raw_sections.values()}
                if selected_raw_sections is not None else self.detector(configurator.snmp_config)):
            plugin = agent_based_register.get_section_plugin(section_name)
            if not isinstance(plugin, SNMPSectionPlugin):
                self._logger.debug("%s: No such section definition", section_name)
                continue

            if section_name in self._fetched_raw_section_names:
                continue

            # This checks data is configured to be persisted (snmp_fetch_interval) and recent enough.
            # Skip gathering new data here. The persisted data will be added later
            if self._persisted_sections and section_name in self._persisted_sections:
                self._logger.debug("%s: Skip fetching data (persisted info exists)", section_name)
                continue

            oid_infos[section_name] = plugin.trees
        return oid_infos

    @staticmethod
    def _sort_section_names(section_names: Set[SectionName]) -> List[SectionName]:
        # In former Check_MK versions (<=1.4.0) CPU check plugins were
        # checked before other check plugins like interface checks.
        # In Check_MK versions >= 1.5.0 the order is random and
        # interface check plugins are executed before CPU check plugins.
        # This leads to high CPU utilization sent by device. Thus we have
        # to re-order the check plugin names.
        # There are some nested check plugin names which have to be considered, too.
        #   for f in $(grep "service_description.*CPU [^lL]" -m1 * | cut -d":" -f1); do
        #   if grep -q "snmp_info" $f; then echo $f; fi done
        cpu_sections_without_cpu_in_name = {
            SectionName("brocade_sys"),
            SectionName("bvip_util"),
        }
        return sorted(section_names,
                      key=lambda x:
                      (not ('cpu' in str(x) or x in cpu_sections_without_cpu_in_name), x))

    def _parse(self, raw_data: SNMPRawData) -> SNMPHostSections:
        persisted_sections = self._extract_persisted_sections(
            raw_data,
            self.configurator.host_config,
        )
        return SNMPHostSections(raw_data, persisted_sections=persisted_sections)

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
