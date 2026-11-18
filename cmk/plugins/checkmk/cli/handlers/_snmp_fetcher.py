#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container

import cmk.utils.paths
from cmk.base.config import LoadingResult
from cmk.base.configlib.fetchers import make_parsed_snmp_fetch_intervals_config
from cmk.ccc.exceptions import OnError
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections, SNMPFetcherConfig
from cmk.checkengine.parser import NO_SELECTION, SectionNameCollection
from cmk.checkengine.plugins import SectionName
from cmk.checkengine.snmplib import SNMPBackendEnum, SNMPSectionName


def snmp_section_selection(
    selected_sections: SectionNameCollection, snmp_sections: Container[SectionName]
) -> frozenset[SNMPSectionName] | NoSelectedSNMPSections:
    if selected_sections is NO_SELECTION:
        return NoSelectedSNMPSections()
    return frozenset(SNMPSectionName(n) for n in selected_sections if n in snmp_sections)


def snmp_fetcher_config(
    loading_result: LoadingResult,
    selected_sections: frozenset[SNMPSectionName] | NoSelectedSNMPSections,
    *,
    on_error: OnError,
    backend_override: SNMPBackendEnum | None,
    force_stored_walks: bool,
    debug: bool,
) -> SNMPFetcherConfig:
    config_cache = loading_result.config_cache
    return SNMPFetcherConfig(
        on_error=on_error,
        missing_sys_description=config_cache.missing_sys_description,
        selected_sections=selected_sections,
        backend_override=backend_override,
        base_path=cmk.utils.paths.omd_root,
        relative_stored_walk_path=cmk.utils.paths.relative_snmpwalks_dir,
        relative_walk_cache_path=cmk.utils.paths.relative_walk_cache_dir,
        relative_section_cache_path=cmk.utils.paths.relative_snmp_section_cache_dir,
        caching_config=make_parsed_snmp_fetch_intervals_config(
            loading_result.loaded_config,
            config_cache.ruleset_matcher,
            config_cache.label_manager.labels_of_host,
        ),
        force_stored_walks=force_stored_walks,
        debug=debug,
    )
