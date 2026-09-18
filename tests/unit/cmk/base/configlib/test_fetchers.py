#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Iterable, Mapping

from cmk.base.configlib.fetchers import (
    make_metrics_identity_routing_config,
    make_telemetry_custom_service_config,
)
from cmk.base.configlib.loaded_config import BaseConfig
from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.matcher import RulesetMatcher, RuleSpec
from tests.testlib.common.empty_config import EMPTY_CONFIG

_MATCHING = HostName("matching-host")
_OTHER = HostName("other-host")

_RULE_VALUE: Mapping[str, object] = {"some-future-option": "value"}


def _config_with_rule_for(host: HostName) -> BaseConfig:
    """Config with a telemetry_custom_service rule conditioned on a single host."""
    rule: RuleSpec[Mapping[str, object]] = RuleSpec(
        value=_RULE_VALUE,
        condition={"host_name": [host]},
        id="test-rule",
    )
    return dataclasses.replace(EMPTY_CONFIG, telemetry_custom_service=[rule])


def _matcher_with_hosts(hosts: Iterable[HostName]) -> RulesetMatcher:
    known = frozenset(hosts)
    return RulesetMatcher(
        host_tags={h: {} for h in known},
        host_paths={},
        all_configured_hosts=known,
        clusters_of={},
        nodes_of={},
    )


def test_telemetry_custom_service_matches_the_host() -> None:
    resolve = make_telemetry_custom_service_config(
        _config_with_rule_for(_MATCHING),
        _matcher_with_hosts((_MATCHING, _OTHER)),
        lambda _: {},
    )

    assert resolve(_MATCHING) == [_RULE_VALUE]


def test_telemetry_custom_service_misses_other_hosts() -> None:
    resolve = make_telemetry_custom_service_config(
        _config_with_rule_for(_MATCHING),
        _matcher_with_hosts((_MATCHING, _OTHER)),
        lambda _: {},
    )

    assert resolve(_OTHER) == []


def test_telemetry_custom_service_collects_every_matching_rule() -> None:
    """The ruleset's eval type is ALL, so all matching rules contribute, in rule order."""
    rules: list[RuleSpec[Mapping[str, object]]] = [
        RuleSpec(value={"nr": 1}, condition={"host_name": [_MATCHING]}, id="first"),
        RuleSpec(value={"nr": 2}, condition={"host_name": [_MATCHING]}, id="second"),
    ]
    resolve = make_telemetry_custom_service_config(
        dataclasses.replace(EMPTY_CONFIG, telemetry_custom_service=rules),
        _matcher_with_hosts((_MATCHING,)),
        lambda _: {},
    )

    assert resolve(_MATCHING) == [{"nr": 1}, {"nr": 2}]


def test_telemetry_custom_service_without_rules() -> None:
    resolve = make_telemetry_custom_service_config(
        EMPTY_CONFIG,
        _matcher_with_hosts((_MATCHING,)),
        lambda _: {},
    )

    assert resolve(_MATCHING) == []


_ROUTING_VALUE: Mapping[str, object] = {"filters": ("all_identity_labels", None)}


def test_metrics_identity_routing_matches_the_host() -> None:
    rule: RuleSpec[Mapping[str, object]] = RuleSpec(
        value=_ROUTING_VALUE,
        condition={"host_name": [_MATCHING]},
        id="test-rule",
    )
    resolve = make_metrics_identity_routing_config(
        dataclasses.replace(EMPTY_CONFIG, metrics_identity_routing=[rule]),
        _matcher_with_hosts((_MATCHING, _OTHER)),
        lambda _: {},
    )

    assert resolve(_MATCHING) == _ROUTING_VALUE


def test_metrics_identity_routing_misses_other_hosts() -> None:
    rule: RuleSpec[Mapping[str, object]] = RuleSpec(
        value=_ROUTING_VALUE,
        condition={"host_name": [_MATCHING]},
        id="test-rule",
    )
    resolve = make_metrics_identity_routing_config(
        dataclasses.replace(EMPTY_CONFIG, metrics_identity_routing=[rule]),
        _matcher_with_hosts((_MATCHING, _OTHER)),
        lambda _: {},
    )

    assert resolve(_OTHER) == {}


def test_metrics_identity_routing_lets_the_topmost_matching_rule_win() -> None:
    """The ruleset's eval type is MERGE and its value has a single key, so a more
    specific rule above a broad one replaces it rather than adding to it."""
    rules: list[RuleSpec[Mapping[str, object]]] = [
        RuleSpec(
            value={"filters": ("specific", None)},
            condition={"host_name": [_MATCHING]},
            id="specific",
        ),
        RuleSpec(value={"filters": ("catch_all", None)}, condition={}, id="catch-all"),
    ]
    resolve = make_metrics_identity_routing_config(
        dataclasses.replace(EMPTY_CONFIG, metrics_identity_routing=rules),
        _matcher_with_hosts((_MATCHING, _OTHER)),
        lambda _: {},
    )

    assert resolve(_MATCHING) == {"filters": ("specific", None)}


def test_metrics_identity_routing_without_rules() -> None:
    resolve = make_metrics_identity_routing_config(
        EMPTY_CONFIG,
        _matcher_with_hosts((_MATCHING,)),
        lambda _: {},
    )

    assert resolve(_MATCHING) == {}
