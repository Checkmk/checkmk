#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Converting legacy rules one by one must not change what they say together.

The legacy ruleset is built for partially filled rules: its help text says that
"the rule execution is done on a per parameter base". The unified ruleset merges
the same way, so converting each rule on its own has to commute with merging.
A converted rule that carries a value its legacy rule never named would answer
for every rule below it.
"""

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.update_config.plugins.lib.mk_oracle_migration import convert, dump


def _merge(rules: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Merge rules, most specific first, as boil_down_agent_rules does.

    See the Matchtype.DICT branch of boil_down_agent_rules in
    non-free/packages/cmk-bakery/cmk/bakery/base/config.py.
    """
    return {key: value for rule in rules[::-1] for key, value in rule.items()}


_GENERAL: Mapping[str, Any] = {
    "activated": True,
    "login": {"auth": ("explicit", ("monitor", ("password", "pw"))), "host": "db1", "port": 1600},
    "sections": {"instance": "sync", "iostats": "async"},
    "remote_instances": [{"sid": "ORCL", "piggyhost": "orcl.example"}],
    "tns_admin": "/etc/oracle",
}

_PARTIAL_RULES: Mapping[str, Mapping[str, object]] = {
    "permission check only": {"validate_permissions": "disable"},
    "discovery filter only": {"sids": ("only", ["ORCL"])},
    "cache age only": {"async_interval": 120},
    "tns_admin only": {"tns_admin": "/opt/oracle"},
    "deactivation only": {"activated": False},
    "another host only": {"login": {"host": "db2"}},
    "another section selection only": {"sections": {"locks": "async"}},
}


@pytest.mark.parametrize("specific", _PARTIAL_RULES.values(), ids=_PARTIAL_RULES.keys())
def test_converting_each_rule_says_what_converting_the_merged_rules_says(
    specific: Mapping[str, object],
) -> None:
    convert_then_merge = _merge([dump(convert(specific).rule), dump(convert(_GENERAL).rule)])
    merge_then_convert = dump(convert(_merge([specific, _GENERAL])).rule)
    assert convert_then_merge == merge_then_convert


def test_a_rule_that_says_nothing_converts_to_a_rule_that_says_nothing() -> None:
    # Every key a conversion writes on its own would win the merge against a
    # more general rule that names it.
    assert dump(convert({}).rule) == {}
