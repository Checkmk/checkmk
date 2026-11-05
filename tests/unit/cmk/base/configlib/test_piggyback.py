#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import time
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

import pytest

from cmk.base.configlib.loaded_config import BaseConfig
from cmk.base.configlib.piggyback import (
    guess_piggybacked_hosts_time_settings,
    make_piggyback_time_settings,
)
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.piggyback import backend as piggyback_backend
from cmk.ruleset_matcher.matcher import RulesetMatcher, RuleSpec
from cmk.utils.paths import omd_root
from tests.testlib.unit.empty_config import EMPTY_CONFIG

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


def _config_with_source_rule(source: HostName) -> BaseConfig:
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


_GLOBAL_MAX_CACHE_AGE = 6666


class _EffectiveTimeSettings(NamedTuple):
    max_cache_age: int = _GLOBAL_MAX_CACHE_AGE
    validity_period: int = 0
    validity_state: int = 0


def _eval_effective_time_settings(
    rule_per_source: Mapping[HostName, Mapping[str, object]],
    piggybacked: HostAddress,
    source: HostName,
) -> _EffectiveTimeSettings:
    sources = sorted({*rule_per_source, source})
    config_from_rules = dataclasses.replace(
        EMPTY_CONFIG,
        piggyback_max_cachefile_age=_GLOBAL_MAX_CACHE_AGE,
        piggybacked_host_files=[
            RuleSpec(value=value, condition={"host_name": [name]}, id=f"rule-{name}")
            for name, value in rule_per_source.items()
        ],
    )
    matcher = RulesetMatcher(
        host_tags={name: {} for name in sources},
        host_paths={},
        all_configured_hosts=frozenset(sources),
        clusters_of={},
        nodes_of={},
    )
    piggyback_config = piggyback_backend.Config(
        piggybacked,
        make_piggyback_time_settings(config_from_rules, matcher, lambda _: {}, sources),
    )
    return _EffectiveTimeSettings(
        max_cache_age=piggyback_config.max_cache_age(source),
        validity_period=piggyback_config.validity_period(source),
        validity_state=piggyback_config.validity_state(source),
    )


_VALIDITY = {"period": 60, "check_mk_state": 2}


@pytest.mark.parametrize(
    "rule_per_source, source, expected",
    [
        pytest.param({}, HostName("src"), _EffectiveTimeSettings(), id="no rule: global default"),
        pytest.param({HostName("src"): {"global_max_cache_age": "global"}}, HostName("src"), _EffectiveTimeSettings(), id="'global' falls back to global default"),
        pytest.param({HostName("src"): {"global_max_cache_age": 100}}, HostName("src"), _EffectiveTimeSettings(max_cache_age=100), id="explicit max cache age"),
        pytest.param({HostName("src"): {"global_validity": _VALIDITY}}, HostName("src"), _EffectiveTimeSettings(validity_period=60, validity_state=2), id="source validity"),
        pytest.param({HostName("src"): {"global_validity": _VALIDITY}}, HostName("other"), _EffectiveTimeSettings(), id="validity not applied to other source"),
    ],
)  # fmt: skip
def test_source_settings_for_piggybacked_host(
    rule_per_source: Mapping[HostName, Mapping[str, object]],
    source: HostName,
    expected: _EffectiveTimeSettings,
) -> None:
    assert _eval_effective_time_settings(rule_per_source, HostAddress("vm1"), source) == expected


@pytest.mark.parametrize(
    "source, expected",
    [
        pytest.param(HostName("srcA"), 100, id="srcA"),
        pytest.param(HostName("srcB"), 200, id="srcB"),
        pytest.param(HostName("srcC"), _GLOBAL_MAX_CACHE_AGE, id="srcC without rule"),
    ],
)  # fmt: skip
def test_each_source_gets_its_own_max_cache_age(source: HostName, expected: int) -> None:
    rule_per_source = {
        HostName("srcA"): {"global_max_cache_age": 100},
        HostName("srcB"): {"global_max_cache_age": 200},
    }
    assert (
        _eval_effective_time_settings(rule_per_source, HostAddress("vm2"), source).max_cache_age
        == expected
    )


def _exemption(*conditions: tuple[str, str], **values: object) -> Mapping[str, object]:
    return {"piggybacked_hostname_conditions": list(conditions), **values}


@pytest.mark.parametrize(
    "rule, piggybacked, expected",
    [
        pytest.param({"global_max_cache_age": 100, "per_piggybacked_host": [_exemption(("exact_match", "vm1"), max_cache_age=50)]}, "vm1", _EffectiveTimeSettings(max_cache_age=50), id="exact match: matching host"),
        pytest.param({"global_max_cache_age": 100, "per_piggybacked_host": [_exemption(("exact_match", "vm1"), max_cache_age=50)]}, "vm2", _EffectiveTimeSettings(max_cache_age=100), id="exact match: other host"),
        pytest.param({"per_piggybacked_host": [_exemption(("regular_expression", "vm"), max_cache_age=10)]}, "vmware", _EffectiveTimeSettings(max_cache_age=10), id="regex matches start"),
        pytest.param({"per_piggybacked_host": [_exemption(("regular_expression", "vm"), max_cache_age=10)]}, "my-vm", _EffectiveTimeSettings(), id="regex not anchored elsewhere"),
        pytest.param({"per_piggybacked_host": [_exemption(("exact_match", "vm1"), ("exact_match", "vm2"), max_cache_age=10)]}, "vm1", _EffectiveTimeSettings(max_cache_age=10), id="several conditions: first"),
        pytest.param({"per_piggybacked_host": [_exemption(("exact_match", "vm1"), ("exact_match", "vm2"), max_cache_age=10)]}, "vm2", _EffectiveTimeSettings(max_cache_age=10), id="several conditions: second"),
        pytest.param({"global_max_cache_age": 100, "per_piggybacked_host": [_exemption(("regular_expression", "^db"), max_cache_age=10)]}, "web1", _EffectiveTimeSettings(max_cache_age=100), id="non-matching regex: source value"),
        pytest.param({"per_piggybacked_host": [_exemption(("exact_match", "vm1"), max_cache_age=10), _exemption(("regular_expression", "vm"), max_cache_age=20)]}, "vm1", _EffectiveTimeSettings(max_cache_age=10), id="first matching exemption wins"),
        pytest.param({"global_max_cache_age": 100, "global_validity": _VALIDITY, "per_piggybacked_host": [_exemption(("exact_match", "vm1"), max_cache_age="global", validity={"period": 5})]}, "vm1", _EffectiveTimeSettings(max_cache_age=100, validity_period=5, validity_state=2), id="each value falls back separately"),
        pytest.param({"global_validity": _VALIDITY, "per_piggybacked_host": [_exemption(("exact_match", "vm1"), max_cache_age=50)]}, "vm1", _EffectiveTimeSettings(max_cache_age=50, validity_period=60, validity_state=2), id="exemption without validity keeps source validity"),
    ],
)  # fmt: skip
def test_exemption_for_piggybacked_host(
    rule: Mapping[str, object], piggybacked: str, expected: _EffectiveTimeSettings
) -> None:
    assert (
        _eval_effective_time_settings(
            {HostName("src"): rule}, HostAddress(piggybacked), HostName("src")
        )
        == expected
    )
