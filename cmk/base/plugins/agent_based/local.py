#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# 0 Service_FOO V=1 This Check is OK
# 1 Bar_Service - This is WARNING and has no performance data
# 2 NotGood V=120;50;100;0;1000 A critical check
# P Some_other_Service value1=10;30;50|value2=20;10:20;0:50;0;100 Result is computed from two values
# P This_is_OK foo=18;20;50
# P Some_yet_other_Service temp=40;30;50|humidity=28;50:100;0:50;0;100
# P Has-no-var - This has no variable
# P No-Text hirn=-8;-20
import time
import re
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    IgnoreResults,
    Metric,
    register,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.clusterize import make_node_notice_results
from .agent_based_api.v1.render import datetime, timespan
from .utils.cache_helper import CacheInfo, render_cache_info

Perfdata = NamedTuple("Perfdata", [
    ("name", str),
    ("value", float),
    ("levels", Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]),
    ("tuple", Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float],
                    Optional[float]]),
])

LocalResult = NamedTuple("LocalResult", [
    ("cached", Optional[CacheInfo]),
    ("item", str),
    ("state", Union[int, str]),
    ("text", str),
    ("perfdata", List[Perfdata]),
])


class LocalError(NamedTuple):
    output: str
    reason: str


class LocalSection(NamedTuple):
    errors: Mapping[str, LocalError]
    data: Mapping[str, LocalResult]


def float_ignore_uom(value):
    '''16MB -> 16.0'''
    while value:
        try:
            return float(value)
        except ValueError:
            value = value[:-1]
    return 0.0


def _try_convert_to_float(value):
    try:
        return float(value)
    except ValueError:
        return None


def _parse_cache(cache_raw, now):
    """add cache info, if found"""
    if not cache_raw:
        return None

    creation_time, interval = (float(v) for v in cache_raw[7:-1].split(',', 1))
    age = now - creation_time

    # make sure max(..) will give the oldest/most outdated case
    return CacheInfo(age=age, cache_interval=interval)


def _split_check_result(line: str):
    """Parse the output of a local check and return the individual components
    Note: this regex does not check the validity of each component. E.g. the state component
          could be 'NOK' (which is not a valid state) but would be complained later

    >>> _split_check_result('0 "Service Name" temp=37.2;30|humidity=28;50:100 Some text')
    ('0', 'Service Name', 'temp=37.2;30|humidity=28;50:100', 'Some text')

    >>> _split_check_result("0 'Service Name' - Some text")
    ('0', 'Service Name', '-', 'Some text')

    >>> _split_check_result('NOK Service_name -')
    ('NOK', 'Service_name', '-', None)
    """
    forbidden_service_name_characters = r"\"\'"
    match = re.match(
        r"^"
        r"([^ ]+) "  # -                                   - service state (permissive)
        r"((\"([^%s]+)\")|(\'([^%s]+)\')|([^ %s]+)) "  # - - optionally quoted service name
        r"([^ ]+)"  # -                                    - perf data
        r"( +(.*))?"  # -                                  - service string
        r"$" % ((forbidden_service_name_characters,) * 3),
        line,
    )
    return (None if match is None else (
        match.groups()[0] or "",
        match.groups()[5] or match.groups()[3] or match.groups()[1] or "",
        match.groups()[7] or "",
        match.groups()[9],
    ))


def _sanitize_state(raw_state):
    try:
        raw_state = int(raw_state)
    except ValueError:
        pass
    if raw_state not in ('P', 0, 1, 2, 3):
        return 3, "Invalid plugin status %r. " % raw_state
    return raw_state, ""


def _parse_perfentry(entry):
    '''parse single perfdata entry

    return a named tuple containing check_levels compatible levels field, as well as
    cmk.base compatible perfdata 6-tuple.

    This function may raise Index- or ValueErrors.

    >>> _parse_perfentry("a=5;3:7;2:8;1;9")
    Perfdata(name='a', value=5.0, levels=(7.0, 8.0, 3.0, 2.0), tuple=('a', 5.0, 7.0, 8.0, 1.0, 9.0))
    >>> _parse_perfentry("a=5;;;;")
    Perfdata(name='a', value=5.0, levels=(None, None, None, None), tuple=('a', 5.0, None, None, None, None))
    >>> _parse_perfentry("a=5;7;2:8;;")
    Perfdata(name='a', value=5.0, levels=(7.0, 8.0, None, 2.0), tuple=('a', 5.0, 7.0, 8.0, None, None))
    >>> _parse_perfentry("a=5;7;2:8;0;")
    Perfdata(name='a', value=5.0, levels=(7.0, 8.0, None, 2.0), tuple=('a', 5.0, 7.0, 8.0, 0.0, None))
    >>> _parse_perfentry("a=5;7;2:8;;20")
    Perfdata(name='a', value=5.0, levels=(7.0, 8.0, None, 2.0), tuple=('a', 5.0, 7.0, 8.0, None, 20.0))
    '''
    entry = entry.rstrip(";")
    name, raw = entry.split('=', 1)
    raw = raw.split(";")
    value = float_ignore_uom(raw[0])

    # create a check_levels compatible levels quadruple
    levels = [None] * 4
    if len(raw) >= 2:
        warn = raw[1].split(':', 1)
        levels[0] = _try_convert_to_float(warn[-1])
        if len(warn) > 1:
            levels[2] = _try_convert_to_float(warn[0])
    if len(raw) >= 3:
        crit = raw[2].split(':', 1)
        levels[1] = _try_convert_to_float(crit[-1])
        if len(crit) > 1:
            levels[3] = _try_convert_to_float(crit[0])

    # only the critical level can be set, in this case warning will be equal to critical
    if levels[0] is None and levels[1] is not None:
        levels[0] = levels[1]

    # create valid perfdata 6-tuple
    min_ = _try_convert_to_float(raw[3]) if len(raw) >= 4 else None
    max_ = _try_convert_to_float(raw[4]) if len(raw) >= 5 else None
    tuple_ = (name, value, levels[0], levels[1], min_, max_)

    # check_levels won't handle crit=None, if warn is present.
    if levels[0] is not None and levels[1] is None:
        levels[1] = float('inf')
    if levels[2] is not None and levels[3] is None:
        levels[3] = float('-inf')

    return Perfdata(name, value, (levels[0], levels[1], levels[2], levels[3]), tuple_)


def _parse_perftxt(string):
    if string == '-':
        return [], ""

    perfdata = []
    msg = []
    for entry in string.split('|'):
        try:
            perfdata.append(_parse_perfentry(entry))
        except (ValueError, IndexError):
            msg.append(entry)
    if msg:
        return perfdata, "Invalid performance data: %r. " % "|".join(msg)
    return perfdata, ""


def parse_local(string_table):
    now = time.time()
    errors = {}
    data = {}
    for line in (l[0] if len(l) == 1 else " ".join(l) for l in string_table):
        # divide optional cache-info and whitespace-stripped rest
        split_cache_match = re.match(r"^(cached\(\d+,\d+\))? *(.*) *$", line)
        assert split_cache_match
        raw_cached, raw_result = split_cache_match.groups()

        if not raw_result:
            continue

        raw_components = _split_check_result(raw_result)
        if not raw_components:
            continue

        # these are raw components - not checked for validity yet
        raw_state, raw_item, raw_perf, raw_info = raw_components

        item = raw_item

        raw_state, state_msg = _sanitize_state(raw_state)
        if state_msg:
            errors[item] = LocalError(output=line, reason=state_msg)
            continue

        perfdata, perf_msg = _parse_perftxt(raw_perf)
        if perf_msg:
            errors[item] = LocalError(output=line, reason=perf_msg)
            continue

        # convert escaped newline chars
        # (will be converted back later individually for the different cores)
        # convert escaped newline chars
        # (will be converted back later individually for the different cores)
        text = (raw_info or "").replace("\\n", "\n")
        if state_msg or perf_msg:
            raw_state = 3
            text = "%s%sOutput is: %s" % (state_msg, perf_msg, text)

        data[item] = LocalResult(
            cached=_parse_cache(raw_cached, now),
            item=item,
            state=raw_state,
            text=text,
            perfdata=perfdata,
        )

    return LocalSection(errors=errors, data=data)


register.agent_section(
    name="local",
    parse_function=parse_local,
)

_STATE_MARKERS = {
    State.OK: "",
    State.WARN: "(!)",
    State.UNKNOWN: "(?)",
    State.CRIT: "(!!)",
}


# Compute state according to warn/crit levels contained in the
# performance data.
def local_compute_state(perfdata, ignore_levels=False):
    for entry in perfdata:
        try:
            _ = Metric(entry.name, 0)
        except TypeError as exc:
            yield Result(
                state=State.WARN,
                summary=f"Invalid metric name: {entry.name!r}",
                details=(f"The metric name {entry.name!r} is invalid. "
                         f"It will not be recorded. Problem: {exc}"),
            )
            metric_name = None
        else:
            metric_name = entry.name

        yield from check_levels(
            entry.value,
            levels_upper=None if ignore_levels else entry.levels[:2],
            levels_lower=None if ignore_levels else entry.levels[2:],
            metric_name=metric_name,
            label=entry.name,
            boundaries=entry.tuple[-2:],
            notice_only=True,
        )


def discover_local(section):
    for key in section.data:
        yield Service(item=key)

    for key in section.errors:
        yield Service(item=key)


def check_local(item: str, params: Mapping[str, Any], section: LocalSection) -> CheckResult:
    local_error = section.errors.get(item)
    if local_error is not None:
        raise ValueError(
            (f'Invalid local check line: "{local_error.output}". Reason: {local_error.reason}'))

    local_result = section.data.get(item)
    if local_result is None:
        return

    try:
        summary, details = local_result.text.split("\n", 1)
    except ValueError:
        summary, details = local_result.text, ""
    if local_result.state != 'P':
        yield Result(
            state=State(local_result.state),
            summary=summary,
            details=details if details else None,
        )
    else:
        if local_result.text:
            yield Result(
                state=State.OK,
                summary=summary,
                details=details if details else None,
            )
    yield from local_compute_state(local_result.perfdata, local_result.state != 'P')

    if local_result.cached is not None:
        value_store = get_value_store()
        if local_result.cached.elapsed_lifetime_percent > 100:
            # normally we include the time-relative cache info in the check
            # output but now the service should go stale, but we can not change
            # the summary of a stale service. The last summary (before going
            # stale) will be displayed until the service is fresh again.
            # To get a valid result we first change the output text to an
            # absolute information and afterwards mark the result as stale.
            if "cache_expired" not in value_store:
                value_store["cache_expired"] = True
                yield Result(
                    state=State.OK,
                    summary=render_cache_info_absolute(local_result.cached),
                )
            else:
                yield IgnoreResults("Cache expired.")
        else:
            value_store.pop("cache_expired", None)
            yield Result(state=State.OK, summary=render_cache_info(local_result.cached))


def render_cache_info_absolute(cacheinfo: CacheInfo) -> str:
    cache_generated = datetime(time.time() - cacheinfo.age)
    return (f"Cache generated {cache_generated}, "
            f"cache interval: {timespan(cacheinfo.cache_interval)}, "
            f"cache lifespan exceeded!")


def cluster_check_local(
    item: str,
    params: Mapping[str, Any],
    section: Dict[str, LocalSection],
) -> CheckResult:

    # collect the result instances and yield the rest
    results_by_node = {}
    collected_ignores: List[IgnoreResults] = []
    for node, node_section in section.items():
        effective_results, ignore_results = _effective_check_result(
            check_local(item, {}, node_section))
        collected_ignores.extend(ignore_results)
        if effective_results and not ignore_results:
            results_by_node[node] = effective_results
    if not results_by_node:
        yield from collected_ignores
        return

    if params is None or params.get("outcome_on_cluster", "worst") == "worst":
        yield from _aggregate_worst(results_by_node)
    else:
        yield from _aggregate_best(results_by_node)


def _effective_check_result(
    node_results: Iterable[Union[IgnoreResults, Metric, Result]],
) -> Tuple[Sequence[Union[Result, Metric]], Sequence[IgnoreResults]]:
    result: List[Union[Result, Metric]] = []
    ignores = []
    for elem in node_results:
        if isinstance(elem, IgnoreResults):
            ignores.append(elem)
        else:
            result.append(elem)
    return result, ignores


def _aggregate_worst(
    node_results: Dict[str, Sequence[Union[Result, Metric]]],
) -> Generator[Union[Result, Metric], None, None]:
    node_states: Dict[State, str] = {}
    for node_name, results in node_results.items():
        node_states.setdefault(
            State.worst(*(r.state for r in results if isinstance(r, Result))),
            node_name,
        )

    global_worst_state = State.worst(*node_states)
    worst_node = node_states[global_worst_state]

    for node_result in node_results[worst_node]:
        if isinstance(node_result, Result):
            yield Result(
                state=node_result.state,
                summary="[%s]: %s" % (worst_node, node_result.summary),
                details="[%s]: %s" % (worst_node, node_result.details),
            )
        else:  # Metric
            yield node_result

    for node, results in node_results.items():
        if node != worst_node:
            yield from make_node_notice_results(node, results)


def _aggregate_best(
    node_results: Dict[str, Sequence[Union[Result, Metric]]],
) -> Generator[Union[Result, Metric], None, None]:
    node_states: Dict[State, str] = {}
    for node_name, results in node_results.items():
        node_states.setdefault(
            State.worst(*(r.state for r in results if isinstance(r, Result))),
            node_name,
        )

    global_best_state = State.best(*node_states)
    best_node = node_states[global_best_state]

    for node_result in node_results[best_node]:
        if isinstance(node_result, Result):
            yield Result(
                state=node_result.state,
                summary="[%s]: %s" % (best_node, node_result.summary),
                details="[%s]: %s" % (best_node, node_result.details),
            )
        else:  # Metric
            yield node_result

    for node, results in node_results.items():
        if node != best_node:
            yield from make_node_notice_results(node, results, force_ok=True)


register.check_plugin(
    name="local",
    service_name="%s",
    discovery_function=discover_local,
    check_default_parameters={},
    check_ruleset_name="local",
    check_function=check_local,
    cluster_check_function=cluster_check_local,
)
