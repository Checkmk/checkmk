#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import time
from collections.abc import Mapping
from pathlib import Path

from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.configlib.piggyback import guess_piggybacked_hosts_time_settings
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.piggyback import backend as piggyback_backend
from cmk.utils.paths import omd_root
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, RuleSpec
from tests.unit.cmk.base.empty_config import EMPTY_CONFIG

_SOURCE_MAX_CACHE_AGE = 300


def _store(source: HostName, piggybacked: HostAddress, omd_root: Path) -> None:
    now = time.time()
    piggyback_backend.store_piggyback_raw_data(
        source_hostname=source,
        piggybacked_raw_data={piggybacked: (b"<<<section>>>\ndata\n",)},
        message_timestamp=now,
        contact_timestamp=now,
        omd_root=omd_root,
    )


def _source_entry(source: HostName) -> tuple[tuple[str, str], str, int]:
    return ("exact_match", source), "max_cache_age", _SOURCE_MAX_CACHE_AGE


def _config_with_source_rule(source: HostName) -> LoadedConfigFragment:
    """Config with piggybacked_host_files rule matching the source host"""
    rule: RuleSpec[Mapping[str, object]] = RuleSpec(
        value={"global_max_cache_age": _SOURCE_MAX_CACHE_AGE},
        condition={"host_name": [source]},
        id="test-rule",
    )
    return dataclasses.replace(EMPTY_CONFIG, piggybacked_host_files=[rule])


def _matcher_with_host(source: HostName) -> RulesetMatcher:
    return RulesetMatcher(
        host_tags={source: {}},
        host_paths={},
        all_configured_hosts=frozenset({source}),
        clusters_of={},
        nodes_of={},
    )


def test_sources_found_under_hostname() -> None:
    hostname = HostName("testhost")
    source = HostName("source-host")
    _store(source, HostAddress(hostname), omd_root)

    result = guess_piggybacked_hosts_time_settings(
        _config_with_source_rule(source),
        _matcher_with_host(source),
        lambda _: {},
        hostname,
        ip_address=None,
    )

    assert _source_entry(source) in result


def test_sources_found_under_ip_address() -> None:
    hostname = HostName("testhost")
    ip = HostAddress("1.2.3.4")
    source = HostName("source-host")
    _store(source, ip, omd_root)

    result = guess_piggybacked_hosts_time_settings(
        _config_with_source_rule(source),
        _matcher_with_host(source),
        lambda _: {},
        hostname,
        ip_address=ip,
    )

    assert _source_entry(source) in result


def test_sources_under_ip_not_found_without_ip_address() -> None:
    hostname = HostName("testhost")
    ip = HostAddress("1.2.3.4")
    source = HostName("source-host")
    _store(source, ip, omd_root)

    result = guess_piggybacked_hosts_time_settings(
        _config_with_source_rule(source),
        _matcher_with_host(source),
        lambda _: {},
        hostname,
        ip_address=None,
    )

    assert _source_entry(source) not in result
