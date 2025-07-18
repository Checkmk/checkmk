#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from functools import lru_cache
from typing import Any as HopeForTheBest
from typing import Final, Literal

from cmk.ccc.hostaddress import HostAddress

_HostCondition = (
    tuple[Literal["exact_match"], str] | tuple[Literal["regular_expression"], str] | None
)
_KeyName = str  # 'max_cache_age', 'validity_period', 'validity_state'
_Value = int


PiggybackTimeSettings = Sequence[tuple[_HostCondition, _KeyName, _Value]]


# 'parse_' is a bit much here. We don't parse everything (yet).
def parse_flattened_piggyback_time_settings(
    host_name: str, rule: Mapping[str, HopeForTheBest]
) -> PiggybackTimeSettings:
    """This rule is a first match rule.

    Max cache age, validity period and state are configurable wihtin this
    rule for all piggybacked host or per piggybacked host of this source.
    In order to differentiate later for which piggybacked hosts a parameter
    is used we flatten this rule to a homogeneous data structure:
        (HOST, KEY, VALUE)
    Then piggyback.py:_get_piggyback_processed_file_info can evaluate the
    parameters generically."""
    flat_rule: list[
        tuple[
            tuple[Literal["exact_match"], str] | tuple[Literal["regular_expression"], str],
            str,
            int,
        ]
    ] = []

    max_cache_age = rule.get("global_max_cache_age")
    if max_cache_age is not None and max_cache_age != "global":
        flat_rule.append((("exact_match", host_name), "max_cache_age", max_cache_age))

    global_validity_setting = rule.get("global_validity", {})

    period = global_validity_setting.get("period")
    if period is not None:
        flat_rule.append((("exact_match", host_name), "validity_period", period))

    check_mk_state = global_validity_setting.get("check_mk_state")
    if check_mk_state is not None:
        flat_rule.append((("exact_match", host_name), "validity_state", check_mk_state))

    for setting in rule.get("per_piggybacked_host", []):
        for piggybacked_hostname_cond in setting["piggybacked_hostname_conditions"]:
            max_cache_age = setting.get("max_cache_age")
            if max_cache_age is not None and max_cache_age != "global":
                flat_rule.append((piggybacked_hostname_cond, "max_cache_age", max_cache_age))

            validity_setting = setting.get("validity", {})
            if not validity_setting:
                continue

            period = validity_setting.get("period")
            if period is not None:
                flat_rule.append((piggybacked_hostname_cond, "validity_period", period))

            check_mk_state = validity_setting.get("check_mk_state")
            if check_mk_state is not None:
                flat_rule.append((piggybacked_hostname_cond, "validity_state", check_mk_state))

    return flat_rule


@lru_cache(maxsize=128)
def _compile(pattern: str) -> re.Pattern:
    """Compile a regular expression pattern and cache the result.

    Caching by the re module is limited to 512 entries.
    We here call the function with no more different arguments then the user
    specified in their configuration, but we might be in the context of checking
    a host, in which case the patterns of various passive services might be much
    more.

    Since we're calling this for every host with a piggyback data source, we'll
    cache the compiled patterns. Since we don't have to share this cache,
    128 entries should be enough.
    """
    return re.compile(pattern)


class Config:
    def __init__(
        self,
        piggybacked_hostname: HostAddress,
        time_settings: PiggybackTimeSettings,
    ) -> None:
        self.piggybacked: Final = piggybacked_hostname
        self._expanded_settings = {
            (host, key): value
            for condition, key, value in reversed(time_settings)
            for host in self._normalize_pattern(condition, piggybacked_hostname)
        }

    @staticmethod
    def _normalize_pattern(
        condition: tuple[Literal["exact_match"], str]
        | tuple[Literal["regular_expression"], str]
        | None,
        piggybacked: HostAddress,
    ) -> Iterable[HostAddress | None]:
        match condition:
            case None:
                yield None
            case ("exact_match", raw_hostname):
                yield HostAddress(raw_hostname)
            case ("regular_expression", hostname_expr):
                if _compile(hostname_expr).match(piggybacked):
                    yield piggybacked
            case _:
                # assert_never(condition) is not understood by mypy here
                raise TypeError(condition)

    def _match(self, key: str, source_hostname: HostAddress) -> int:
        with suppress(KeyError):
            return self._expanded_settings[(self.piggybacked, key)]
        with suppress(KeyError):
            return self._expanded_settings[(source_hostname, key)]
        return self._expanded_settings[(None, key)]

    def max_cache_age(self, source: HostAddress) -> int:
        return self._match("max_cache_age", source)

    def validity_period(self, source: HostAddress) -> int:
        try:
            return self._match("validity_period", source)
        except KeyError:
            return 0

    def validity_state(self, source: HostAddress) -> int:
        try:
            return self._match("validity_state", source)
        except KeyError:
            return 0
