#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import CheckResult, get_rate, get_value_store, render, StringTable


@dataclass(frozen=True)
class Counter:
    value: int
    descr: str


Section = Mapping[str, Counter]
Params = Mapping[str, tuple[float, float]]

# Newer output has MAIN and MGT prefixed keys, MGT takes precedence
_PREFIX_PRECEDENCE = {"MAIN": 1, "MGT": 2}


def parse_varnish(string_table: StringTable) -> Section:
    return {
        _strip_prefix(line[0]): Counter(value, _descr(line[0], line[3:]))
        for line in sorted(
            string_table, key=lambda line: _PREFIX_PRECEDENCE.get(line[0].split(".", 1)[0], 0)
        )
        if (value := _parse_int(line[1])) is not None
    }


def _strip_prefix(key: str) -> str:
    head, _, tail = key.partition(".")
    return tail if head in _PREFIX_PRECEDENCE else key


def _parse_int(raw: str) -> int | None:
    try:
        return int(raw)
    except ValueError:
        return None


def _descr(key: str, words: Sequence[str]) -> str:
    # skip the first word if it repeats the key, e.g. 'client_conn ... Client connections'
    return " ".join(words[1:] if words and words[0].lower() in key else words).replace("/", " ")


def _metric_name(key: str) -> str:
    name = (
        key.replace("n_wrk", "worker", 1)
        if key.startswith("n_wrk")
        else key.replace("n_", "objects_", 1)
        if key.startswith("n_")
        else key
    )
    return f"varnish_{name}_rate"


def check_varnish_stats(params: Params, section: Section, keys: Sequence[str]) -> CheckResult:
    yield from check_varnish_rates(params, section, keys, get_value_store(), time.time())


def check_varnish_rates(
    params: Params,
    section: Section,
    keys: Sequence[str],
    value_store: MutableMapping[str, object],
    now: float,
) -> CheckResult:
    for key in (k for k in keys if k in section):
        counter = section[key]
        yield from check_levels(
            get_rate(value_store, f"varnish.{key}", now, counter.value, raise_overflow=True),
            _metric_name(key),
            params.get(key.split("_", 1)[-1], (None, None)),
            human_readable_func=lambda r, d=f"{counter.descr}/s": f"{r:.1f} {d}",
        )


def check_varnish_ratio(
    params: Params, section: Section, ratio_keys: tuple[str, str, str]
) -> CheckResult:
    reference_key, additional_key, metric_name = ratio_keys
    reference = section[reference_key].value
    total = reference + section[additional_key].value
    warn, crit = params["levels_lower"]
    yield from check_levels(
        100.0 * reference / total if total > 0 else 0.0,
        metric_name,
        (None, None, warn, crit),
        human_readable_func=render.percent,
    )
