#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is only to help the migration process.
# I don't want to invest time into improving the typing here, but rather
# focus on getting rid of the legacy plug-ins as soon as possible.

# mypy: disable-error-code="type-arg"


import itertools
from collections import defaultdict
from collections.abc import Generator, Sequence
from contextlib import suppress

from cmk.agent_based.v2 import CheckResult, IgnoreResults, Metric, Result, State


def convert_legacy_results(
    subresults: Sequence[tuple[int, str, list] | Result | Metric | IgnoreResults],
) -> CheckResult:
    for idx, subresult in enumerate(subresults):
        if isinstance(subresult, Result | Metric | IgnoreResults):
            yield subresult
            continue

        if "\n" in subresult[1]:
            yield from _create_new_results_with_details(subresults[idx:])
            break

        yield from _create_new_result(*subresult)


def _create_new_results_with_details(
    results: Sequence,
) -> CheckResult:
    state_sorted = defaultdict(list)
    for result in results:
        if isinstance(result, Result | Metric):
            yield result
            continue
        state = State(result[0])
        state_sorted[state].append(result)

    for idx, (state, subresults) in enumerate(state_sorted.items()):
        metrics = []
        details = []
        first_detail = subresults[0][1] if subresults else ""
        for result in subresults:
            if len(result) > 2:
                metrics.extend(list(result[2]))
            details.extend([el for el in result[1].split("\n") if el])

        if len(details) == 0:
            continue

        # we might have an actual summary to use
        if idx == 0 and (s := first_detail.split("\n", 1)[0]):
            summary = s
        else:
            summary = (
                f"{len(details)} additional detail{'' if len(details) == 1 else 's'} available"
            )

        yield Result(
            state=state,
            summary=summary,
            details="\n".join(d.lstrip() for d in details),
        )
        yield from _create_new_metric(metrics)


def _get_float(raw_value: object) -> float | None:
    """Try to convert to float

    >>> _get_float("12.3s")
    12.3

    """
    with suppress(TypeError, ValueError):
        return float(raw_value)  # type: ignore[arg-type]

    if not isinstance(raw_value, str):
        return None
    # try to cut off units:
    for i in range(len(raw_value) - 1, 0, -1):
        with suppress(TypeError, ValueError):
            return float(raw_value[:i])

    return None


def _create_new_result(
    legacy_state: int,
    legacy_text: str,
    legacy_metrics: tuple | list = (),
) -> CheckResult:
    if legacy_state or legacy_text:  # skip "Null"-Result
        yield Result(state=State(legacy_state), summary=legacy_text.strip())
    yield from _create_new_metric(legacy_metrics)


def _create_new_metric(legacy_metrics: tuple | list = ()) -> Generator[Metric]:
    for metric in legacy_metrics:
        if len(metric) < 2:
            continue
        name = str(metric[0])
        value = _get_float(metric[1])
        if value is None:  # skip bogus metrics
            continue
        # fill up with None:
        warn, crit, min_, max_ = (
            _get_float(v) for v, _ in itertools.zip_longest(metric[2:], range(4))
        )
        yield Metric(name, value, levels=(warn, crit), boundaries=(min_, max_))
