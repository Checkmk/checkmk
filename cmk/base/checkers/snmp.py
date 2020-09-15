#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import logging
from pathlib import Path
from typing import Any, Dict, Final, Iterable, List, Optional, Sequence, Set

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

from cmk.fetchers import factory, FetcherType

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin
from cmk.base.config import SelectedRawSections

from ._abstract import (
    ABCSource,
    ABCChecker,
    ABCHostSections,
    ABCParser,
    ABCSummarizer,
    Mode,
)
from ._cache import SectionStore


class SNMPHostSections(ABCHostSections[SNMPRawData, SNMPSections, SNMPPersistedSections,
                                       SNMPSectionContent]):
    pass


class CachedSNMPDetector:
    """Object to run/cache SNMP detection"""
    def __init__(self, logger: logging.Logger) -> None:
        super(CachedSNMPDetector, self).__init__()
        self._logger = logger
        # Optional set: None: we never tried, empty: we tried, but found nothing
        self._cached_result: Optional[Set[SectionName]] = None

    # TODO (mo): Make this (and the called) function(s) return the sections directly!
    def __call__(
        self,
        snmp_config: SNMPHostConfig,
        sections: Iterable[SNMPScanSection],
        *,
        on_error,
    ) -> Set[SectionName]:
        """Returns a list of raw sections that shall be processed by this source.

        The logic is only processed once. Once processed, the answer is cached.
        """
        if self._cached_result is None:
            self._cached_result = gather_available_raw_section_names(
                sections,
                on_error=on_error,
                missing_sys_description=config.get_config_cache().in_binary_hostlist(
                    snmp_config.hostname,
                    config.snmp_without_sys_descr,
                ),
                backend=factory.backend(snmp_config, logger=self._logger),
            )
        return self._cached_result


class SNMPSource(ABCSource[SNMPRawData, SNMPHostSections]):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: HostAddress,
        *,
        mode: Mode,
        source_type: SourceType,
        id_: str,
        cpu_tracking_id: str,
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
            cpu_tracking_id=cpu_tracking_id,
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
        ip_lookup.verify_ipaddress(self.ipaddress)
        self.snmp_config = (
            # Because of crap inheritance.
            self.host_config.snmp_config(self.ipaddress)
            if self.source_type is SourceType.HOST else self.host_config.management_snmp_config)
        self.on_snmp_scan_error = on_error
        self.detector: Final = CachedSNMPDetector(self._logger)
        # Attributes below are wrong
        self.use_snmpwalk_cache = True
        self.ignore_check_interval = False
        self.prefetched_sections: Sequence[SectionName] = ()
        self.section_store: SectionStore[SNMPPersistedSections] = SectionStore(
            self.persisted_sections_file_path,
            self._logger,
        )

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
            cpu_tracking_id="snmp",
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
            cpu_tracking_id="snmp",
            title="Management board - SNMP",
        )

    def configure_fetcher(self) -> Dict[str, Any]:
        return {
            "file_cache": self.file_cache.configure(),
            "oid_infos": {
                str(name): [tree.to_json() for tree in trees]
                for name, trees in self._make_oid_infos(
                    persisted_sections=self.section_store.load(
                        SNMPChecker._use_outdated_persisted_sections),
                    selected_raw_sections=self.selected_raw_sections,
                    prefetched_sections=self.prefetched_sections,
                ).items()
            },
            "use_snmpwalk_cache": self.use_snmpwalk_cache,
            "snmp_config": self.snmp_config._asdict(),
        }

    def _make_checker(self) -> "SNMPChecker":
        return SNMPChecker(self)

    def _make_parser(self) -> "SNMPParser":
        return SNMPParser(self.hostname, self._logger)

    def _make_summarizer(self) -> "SNMPSummarizer":
        return SNMPSummarizer(self.exit_spec)

    def _make_snmp_scan_sections(self) -> Iterable[SNMPScanSection]:
        """Create list of all SNMP scan specifications.

        Here, we evaluate the rule_dependent_detect_spec-attribute of SNMPSectionPlugin. This
        attribute is not an official part of the API. It allows for dynamically computing SNMP
        detection specifications based on user-defined discovery rulesets. This is needed by some
        check plugins, such as if and if64.

        In case this attribute is not set, we simply use SNMPSectionPlugin.detect_spec, which is
        the official way for specifying detection conditions.
        """
        snmp_scan_sections = []
        config_cache = config.get_config_cache()

        for snmp_section_plugin in agent_based_register.iter_all_snmp_sections():
            if snmp_section_plugin.rule_dependent_detect_spec is None:
                detect_spec = snmp_section_plugin.detect_spec
            else:
                # fetch user-defined discovery rules
                rules_for_host = [
                    config_cache.host_extra_conf(
                        self.hostname,
                        agent_based_register.get_discovery_ruleset(ruleset),
                    ) for ruleset in snmp_section_plugin.rule_dependent_detect_spec.rulesets
                ]
                # call evaluator with these rules, returning an SNMPDetectSpec
                detect_spec = snmp_section_plugin.rule_dependent_detect_spec.evaluator(
                    *rules_for_host)

            snmp_scan_sections.append((snmp_section_plugin.name, detect_spec))

        return snmp_scan_sections

    def _make_oid_infos(
        self,
        *,
        persisted_sections: SNMPPersistedSections,
        selected_raw_sections: Optional[SelectedRawSections],
        prefetched_sections: Sequence[SectionName],
    ) -> Dict[SectionName, List[SNMPTree]]:
        oid_infos = {}  # Dict[SectionName, List[SNMPTree]]
        if selected_raw_sections is None:
            section_names = self.detector(
                self.snmp_config,
                self._make_snmp_scan_sections(),
                on_error=self.on_snmp_scan_error,
            )
        else:
            section_names = {s.name for s in selected_raw_sections.values()}

        section_names -= self.host_config.disabled_snmp_sections()

        for section_name in SNMPSource._sort_section_names(section_names):
            plugin = agent_based_register.get_section_plugin(section_name)
            if not isinstance(plugin, SNMPSectionPlugin):
                self._logger.debug("%s: No such section definition", section_name)
                continue

            if section_name in prefetched_sections:
                continue

            # This checks data is configured to be persisted (snmp_fetch_interval) and recent enough.
            # Skip gathering new data here. The persisted data will be added later
            if section_name in persisted_sections:
                self._logger.debug("%s: Skip fetching data (persisted info exists)", section_name)
                continue

            oid_infos[section_name] = plugin.trees
        return oid_infos

    @staticmethod
    def _sort_section_names(section_names: Iterable[SectionName]) -> Iterable[SectionName]:
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


class SNMPParser(ABCParser[SNMPRawData, SNMPHostSections]):
    """A parser for SNMP data."""
    def _parse(
        self,
        raw_data: SNMPRawData,
    ) -> SNMPHostSections:
        persisted_sections = SNMPParser._extract_persisted_sections(
            raw_data,
            self.host_config,
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


class SNMPSummarizer(ABCSummarizer[SNMPHostSections]):
    def _summarize(self, host_sections: SNMPHostSections) -> ServiceCheckResult:
        return 0, "Success", []


class SNMPChecker(ABCChecker[SNMPRawData, SNMPSections, SNMPPersistedSections, SNMPHostSections]):
    pass
