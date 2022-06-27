#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time

# Example output from agent:
# 0 Service_FOO V=1 This Check is OK
# 1 Bar_Service - This is WARNING and has no performance data
# 2 NotGood V=120;50;100;0;1000 A critical check
# P Some_other_Service value1=10;30;50|value2=20;10:20;0:50;0;100 Result is computed from two values
# P This_is_OK foo=18;20;50
# P Some_yet_other_Service temp=40;30;50|humidity=28;50:100;0:50;0;100
# P Has-no-var - This has no variable
# P No-Text hirn=-8;-20
from typing import Any, Iterable, List, Mapping, NamedTuple, Optional, Sequence, Tuple, Union

from .agent_based_api.v1 import check_levels, Metric, register, Result, Service, State
from .agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from .utils.cache_helper import CacheInfo, render_cache_info

# we don't have IgnoreResults and thus don't want to handle them
LocalCheckResult = Iterable[Union[Metric, Result]]
Levels = Optional[Tuple[float, float]]


class Perfdata(NamedTuple):
    name: str
    value: float
    levels_upper: Levels
    levels_lower: Levels
    boundaries: Optional[Tuple[Optional[float], Optional[float]]]


class LocalResult(NamedTuple):
    cache_info: Optional[CacheInfo]
    item: str
    state: State
    apply_levels: bool
    text: str
    perfdata: Iterable[Perfdata]


class LocalError(NamedTuple):
    output: str
    reason: str


class LocalSection(NamedTuple):
    errors: List[LocalError]
    data: Mapping[str, LocalResult]


def float_ignore_uom(value: str) -> float:
    """16MB -> 16.0"""
    while value:
        try:
            return float(value)
        except ValueError:
            value = value[:-1]
    return 0.0


def _try_convert_to_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except ValueError:
        return None


def _sanitize_state(raw_state: str) -> Tuple[Union[int, str], str]:
    state_mapping: Mapping[str, Tuple[Union[int, str], str]] = {
        "0": (0, ""),
        "1": (1, ""),
        "2": (2, ""),
        "3": (3, ""),
        "P": ("P", ""),
    }
    return state_mapping.get(raw_state, (3, f"Invalid plugin status {raw_state}."))


def _parse_perfentry(entry: str) -> Perfdata:
    """Parse single perfdata entry, syntax is:
        NAME=VALUE[;[[WARN_LOWER:]WARN_UPPER][;[[CRIT_LOWER:]CRIT_UPPER][;[MIN][;MAX]]]]

    see https://docs.checkmk.com/latest/de/localchecks.html
    >>> _parse_perfentry("a=5;3:7;2:8;1;9")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=(3.0, 2.0), boundaries=(1.0, 9.0))
    >>> _parse_perfentry("a=5;7")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, inf), levels_lower=None, boundaries=(None, None))
    >>> _parse_perfentry("a=5")
    Perfdata(name='a', value=5.0, levels_upper=None, levels_lower=None, boundaries=(None, None))
    >>> _parse_perfentry("a=5;7;8")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=None, boundaries=(None, None))
    >>> _parse_perfentry("a=5;7;8;1")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=None, boundaries=(1.0, None))
    >>> _parse_perfentry("a=5;7;8;1;9")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=None, boundaries=(1.0, 9.0))
    >>> _parse_perfentry("a=5;3:7;8;1;9")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=(3.0, -inf), boundaries=(1.0, 9.0))
    >>> _parse_perfentry("a=5;7;2:8;1;9")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=(2.0, 2.0), boundaries=(1.0, 9.0))
    >>> _parse_perfentry("a=5;;;;")
    Perfdata(name='a', value=5.0, levels_upper=None, levels_lower=None, boundaries=(None, None))
    >>> _parse_perfentry("a=5;7;2:8;;")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=(2.0, 2.0), boundaries=(None, None))
    >>> _parse_perfentry("a=5;7;2:8;0;")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=(2.0, 2.0), boundaries=(0.0, None))
    >>> _parse_perfentry("a=5;7;2:8;;20")
    Perfdata(name='a', value=5.0, levels_upper=(7.0, 8.0), levels_lower=(2.0, 2.0), boundaries=(None, 20.0))
    """
    entry = entry.rstrip(";")
    name, raw_list = entry.split("=", 1)
    raw = raw_list.split(";")
    value = float_ignore_uom(raw[0])

    # create a check_levels compatible levels quadruple
    levels: List[Optional[float]] = [None] * 4
    if len(raw) >= 2:
        warn = raw[1].split(":", 1)
        levels[0] = _try_convert_to_float(warn[-1])
        if len(warn) > 1:
            levels[2] = _try_convert_to_float(warn[0])
    if len(raw) >= 3:
        crit = raw[2].split(":", 1)
        levels[1] = _try_convert_to_float(crit[-1])
        if len(crit) > 1:
            levels[3] = _try_convert_to_float(crit[0])

    # the critical level can be set alone, in this case warning will be equal to critical
    if levels[0] is None and levels[1] is not None:
        levels[0] = levels[1]
    if levels[2] is None and levels[3] is not None:
        levels[2] = levels[3]

    # check_levels won't handle crit=None, if warn is present.
    if levels[0] is not None and levels[1] is None:
        levels[1] = float("inf")
    if levels[2] is not None and levels[3] is None:
        levels[3] = float("-inf")

    def optional_tuple(warn: Optional[float], crit: Optional[float]) -> Levels:
        assert (warn is None) == (crit is None)
        if warn is not None and crit is not None:
            return warn, crit
        return None

    return Perfdata(
        name,
        value,
        levels_upper=optional_tuple(levels[0], levels[1]),
        levels_lower=optional_tuple(levels[2], levels[3]),
        boundaries=(
            _try_convert_to_float(raw[3]) if len(raw) >= 4 else None,
            _try_convert_to_float(raw[4]) if len(raw) >= 5 else None,
        ),
    )


def _parse_perftxt(string: str) -> Tuple[Iterable[Perfdata], str]:
    if string == "-":
        return [], ""

    perfdata = []
    msg = []
    for entry in string.split("|"):
        try:
            perfdata.append(_parse_perfentry(entry))
        except (ValueError, IndexError):
            msg.append(entry)
    if msg:
        return perfdata, "Invalid performance data: %r. " % "|".join(msg)
    return perfdata, ""


def _split_check_result(line: str) -> Optional[Tuple[str, str, str, Optional[str]]]:
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
    return (
        None
        if match is None
        else (
            match.groups()[0] or "",
            match.groups()[5] or match.groups()[3] or match.groups()[1] or "",
            match.groups()[7] or "",
            match.groups()[9],
        )
    )


def parse_local(string_table: StringTable) -> LocalSection:
    """
    The local check result is encoded in a single line containing up to 5 - basically white space
    separated - components of which the first and the last one are optional:
    1 [optional] cache specifier "cached(number,number) "
      - terminated by single white space (only if existent)

    2 [mandatory] check result state [0|1|2|3|P]
      - terminated by single white space

    3 [mandatory] item name
      - may contain all characters but double and single quote
      - _might_ be double or single quoted and then containing spaces
      - ! terminated by arbitrary number of white spaces
      - !!! potential abuse: "  " is a valid name :)
      - ! can contain backslashes (used for windows paths)
      - ! can contain strange symbols like &$äöüÄÖÜß

    4 [mandatory] encoded perf data string, may contain same characters as item name + [,;|=+-%]
      - '|', ';' and '=' used as control characters
      - single '-' stands for no perf data
      - ! terminated by EOL or arbitrary number of spaces
      - ! might contain ',' separated floats

    5 [optional] arbitrary text - may contain all encodable characters
      - will not start with spaces (due to regex)
      - "\n" will be replaced by newlines
    """
    # wrap pure counterpart
    return parse_local_pure(string_table, time.time())


def parse_local_pure(string_table: Iterable[Sequence[str]], now: float) -> LocalSection:
    """
    >>> parse_local_pure([['0 "Service Name" - arbitrary info text']], 1617883538).data
    {'Service Name': LocalResult(cache_info=None, item='Service Name', state=<State.OK: 0>, apply_levels=False, text='arbitrary info text', perfdata=[])}
    >>> parse_local_pure([['cached(1617883538,1617883538) 0 "Service Name" - arbitrary info text']], 1617883538).data
    {'Service Name': LocalResult(cache_info=CacheInfo(age=0.0, cache_interval=1617883538.0, elapsed_lifetime_percent=0.0), item='Service Name', state=<State.OK: 0>, apply_levels=False, text='arbitrary info text', perfdata=[])}
    """
    # NOTE: despite applying a regular expression to each line would allow for exact
    #       matching against all syntactical requirements, a single mistake in the line
    #       would make it invalid with no hints about what exactly was the problem.
    #       Therefore we first apply a very loosy pattern to "split" into raw components
    #       and later check those for validity.
    errors = []
    parsed_data = {}

    # turn splittet lines into monolithic strings again in order to be able to handle
    # all input in the same manner. current `local` sections are 0-separated anyway so
    # joining is only needed for legacy input
    for line in (l[0] if len(l) == 1 else " ".join(l) for l in string_table):
        # divide optional cache-info and whitespace-stripped rest
        split_cache_match = re.match(r"^(cached\(\d+,\d+\))? *(.*) *$", line)
        assert split_cache_match
        raw_cached, raw_result = split_cache_match.groups()

        if not raw_result:
            errors.append(
                LocalError(
                    output=line,
                    reason="Received empty line. Maybe some of the local checks"
                    " returns a superfluous newline character.",
                )
            )
            continue

        raw_components = _split_check_result(raw_result)
        if not raw_components:
            # splitting into raw components didn't work out so the given line must
            # be really crappy
            errors.append(
                LocalError(
                    output=line,
                    reason="Received wrong format of local check output. "
                    "Please read the documentation regarding the correct format: "
                    "https://docs.checkmk.com/2.0.0/de/localchecks.html",
                )
            )
            continue

        # these are raw components - not checked for validity yet
        raw_state, raw_item, raw_perf, raw_info = raw_components

        state, state_msg = _sanitize_state(raw_state)
        if state_msg:
            errors.append(LocalError(output=line, reason=state_msg))

        item = raw_item

        perfdata, perf_msg = _parse_perftxt(raw_perf)
        if perf_msg:
            errors.append(LocalError(output=line, reason=perf_msg))

        # convert escaped newline chars
        # (will be converted back later individually for the different cores)
        text = (raw_info or "").replace("\\n", "\n")
        if state_msg or perf_msg:
            state = 3
            text = "%s%sOutput is: %s" % (state_msg, perf_msg, text)

        parsed_data[item] = LocalResult(
            cache_info=CacheInfo.from_raw(raw_cached, now),
            item=item,
            state=State.OK if state == "P" else State(state),
            apply_levels=state == "P",
            text=text,
            perfdata=perfdata,
        )

    return LocalSection(errors=errors, data=parsed_data)


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
def _local_make_metrics(local_result: LocalResult) -> LocalCheckResult:
    for entry in local_result.perfdata:
        try:
            _ = Metric(entry.name, 0)
        except TypeError as exc:
            yield Result(
                state=State.WARN,
                summary=f"Invalid metric name: {entry.name!r}",
                details=(
                    f"The metric name {entry.name!r} is invalid. "
                    f"It will not be recorded. Problem: {exc}"
                ),
            )
            metric_name = None
        else:
            metric_name = entry.name

        yield from check_levels(
            entry.value,
            # check_levels does not like levels like (23, None), but it does deal with it.
            levels_upper=entry.levels_upper if local_result.apply_levels else None,
            levels_lower=entry.levels_lower if local_result.apply_levels else None,
            metric_name=metric_name,
            label=_labelify(entry.name),
            boundaries=entry.boundaries,
        )


def _labelify(word: str) -> str:
    """
    >>> _labelify("INCIDENTS_CT_PHISING")
    'Incidents ct phising'
    >>> _labelify("weekIncidence")
    'Week incidence'
    >>> _labelify("casesPer100k")
    'Cases per 100 k'
    >>> _labelify("WHOrecommendation4")
    'WHO recommendation 4'
    >>> _labelify("recommendation4WHO")
    'Recommendation 4 WHO'
    >>> _labelify("zombie_apocalypse")
    'Zombie apocalypse'

    """
    label = "".join(
        "%s%s"
        % (
            this if not prev.isalnum() or prev.isupper() or nxt.isupper() else this.lower(),
            " "
            if (
                prev.isupper()
                and this.isupper()
                and nxt.islower()
                or this.islower()
                and nxt.isupper()
                or this.isdigit() is not nxt.isdigit()
            )
            else "",
        )
        for prev, this, nxt in zip(" " + word, word, word[1:] + " ")
    )
    if label.isupper():
        label = label.lower()
    return (label[0].upper() + label[1:].replace("_", " ")).strip()


def discover_local(section: LocalSection) -> DiscoveryResult:
    if section.errors:
        output = section.errors[0].output
        reason = section.errors[0].reason
        raise ValueError(
            (
                "Invalid line in agent section <<<local>>>. "
                'Reason: %s First offending line: "%s"' % (reason, output)
            )
        )

    for key in section.data:
        yield Service(item=key)


def check_local(item: str, params: Mapping[str, Any], section: LocalSection) -> LocalCheckResult:
    local_result = section.data.get(item)
    if local_result is None:
        return

    try:
        summary, details = local_result.text.split("\n", 1)
    except ValueError:
        summary, details = local_result.text, ""

    if local_result.text:
        yield Result(
            state=local_result.state,
            summary=summary,
            details=details if details else None,
        )
    yield from _local_make_metrics(local_result)

    if local_result.cache_info is not None:
        yield Result(state=State.OK, summary=render_cache_info(local_result.cache_info))


register.check_plugin(
    name="local",
    service_name="%s",
    discovery_function=discover_local,
    check_default_parameters={},
    check_ruleset_name="local",
    check_function=check_local,
)
