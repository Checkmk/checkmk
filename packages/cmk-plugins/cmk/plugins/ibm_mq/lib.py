#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import re
from collections.abc import Generator, Mapping
from typing import Any

from cmk.agent_based.v2 import IgnoreResultsError, StringTable

Section = Mapping[str, Mapping[str, str]]
ResultType = dict[str, dict[str, str]]

RE_INTRO = re.compile(r"^QMNAME\((.*)\)[\s]*STATUS\((.*?)\)[\s]*NOW\((.*)\)")
RE_GROUP = re.compile(r"^(AMQ\d+\w?:|CSQM\d+\w? !)")
RE_KEY = re.compile(r"([\s]*|CSQM\d+\w? ![A-Z0-9.]+[\s]+)([A-Z0-9]+\()")
RE_SECOND_COLUMN = re.compile(r"[A-Z]+\([^&]*\)$")
RE_KEY_VALUE = re.compile(r"([A-Z0-9]+)\(([^&]*)\)")


def parse_ibm_mq(string_table: StringTable, group_by_object: str) -> Section:
    def record_attribute(s: str, attributes: dict[str, str]) -> None:
        pair = RE_KEY_VALUE.search(s)
        if pair is None:
            return
        key = pair.group(1)
        value = pair.group(2).strip()
        # Do not overwrite existing attributes
        if key in attributes and str(value) in ("", "0", ",", "OFF"):
            return
        attributes[key] = value

    def record_group(qmname: str, attributes: dict[str, str], parsed: ResultType) -> None:
        obj = attributes.get(group_by_object)
        if obj is not None and not obj.startswith(("SYSTEM", "AMQ.MQEXPLORER")):
            obj = f"{qmname}:{obj}"
            parsed.setdefault(obj, {})
            parsed[obj].update(attributes)

    def lookahead(iterable: StringTable) -> Generator[tuple[list[str], bool]]:
        """
        Pass through all values from the given iterable, augmented by the
        information if there are more values to come after the current one
        (True), or if it is the last value (False).
        """
        sentinel = object()
        previous = sentinel
        for value in iter(iterable):
            if isinstance(previous, list) and previous is not sentinel:
                yield previous, True
            previous = value
        if isinstance(previous, list):
            yield previous, False

    parsed: ResultType = {}
    attributes: dict[str, str] = {}
    qmname: str = ""  # TODO: Find some way to avoid setting this dummy value.
    for (line,), has_more in lookahead(string_table):
        intro_line = RE_INTRO.match(line)
        if intro_line:
            if attributes:
                record_group(qmname, attributes, parsed)
                attributes.clear()
            qmname = intro_line.group(1)
            qmstatus = intro_line.group(2)
            now = intro_line.group(3)
            parsed[qmname] = {"STATUS": qmstatus, "NOW": now}
            continue

        if (RE_GROUP.match(line) or not has_more) and attributes:
            record_group(qmname, attributes, parsed)
            attributes.clear()
            # Remote group header can contain attribute(s)

        if RE_KEY.match(line):
            if RE_SECOND_COLUMN.search(line[39:]):
                first_half = line[:40]
                second_half = line[40:]
                record_attribute(first_half, attributes)
                record_attribute(second_half, attributes)
            else:
                record_attribute(line, attributes)
    return parsed


def ibm_mq_check_version(
    actual_version: str | None, params: Mapping[str, Any], label: str
) -> tuple[int, str]:
    """
    >>> ibm_mq_check_version(
    ...    "2.0.0b4",
    ...     {"version": (("at_least", "2.0.0p2"), 2)},
    ...     "Doc test",
    ... )
    (2, 'Doc test: 2.0.0b4 (should be at least 2.0.0p2)')

    """

    def tokenize(version: str) -> list[int]:
        _map_chars = {"p": 2, "b": 1, "i": 0}
        if not set("0123456789.pbi").issuperset(version):
            raise ValueError(version)
        return [
            _map_chars[g] if g in _map_chars else int(g)
            for g in re.findall(r"(\d+|[pbi]+)", version)
        ]

    info = f"{label}: {actual_version}"
    if actual_version is None:
        return 3, info + " (no agent info)"
    if "version" not in params:
        return 0, info
    (comp_type, expected_version), state = params["version"]
    try:
        parts_actual = tokenize(actual_version)
        parts_expected = tokenize(expected_version)
    except ValueError:
        return 3, (
            f"Cannot compare {actual_version} and {expected_version}."
            " Only numbers separated by characters 'b', 'i', 'p', or '.' are allowed for a version."
        )

    if comp_type == "at_least" and parts_actual < parts_expected:
        return state, info + " (should be at least %s)" % expected_version
    if comp_type == "specific" and parts_actual != parts_expected:
        return state, info + " (should be %s)" % expected_version
    return 0, info


def is_ibm_mq_service_vanished(item: str, parsed: Mapping[str, Any]) -> bool:
    """
    Returns true if queue or channel is not contained anymore in the agent
    output but queue manager is known as RUNNING. Throws MKCounterWrapped to
    mark service as STALE if QMGR is not RUNNING.
    """
    if item in parsed:
        return False

    qmgr_name = item.split(":", 1)[0]
    qmgr_status = "RUNNING"
    if qmgr_name in parsed:
        qmgr_status = parsed[qmgr_name]["STATUS"]

    if qmgr_status == "RUNNING":
        return True
    raise IgnoreResultsError("Stale because queue manager %s" % qmgr_status)
