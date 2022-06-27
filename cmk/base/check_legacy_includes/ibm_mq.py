#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Any, Dict

from cmk.base.check_api import MKCounterWrapped, regex


def parse_runmqsc_display_output(info, group_by_object):
    re_intro = regex(r"^QMNAME\((.*)\)[\s]*STATUS\((.*?)\)[\s]*NOW\((.*)\)")
    re_group = regex(r"^AMQ\d+\w?: [^.]*.")
    re_key = regex(r"[\s]*[A-Z0-9]+\(")
    re_second_column = regex(r" [A-Z0-9]+\(")
    re_key_value = regex(r"([A-Z0-9]+)\((.*)\)[\s]*")

    def record_attribute(s, attributes, parsed):
        pair = re_key_value.match(s)
        if pair is None:
            return
        key = pair.group(1)
        value = pair.group(2).strip()
        attributes[key] = value

    def record_group(qmname, attributes, parsed):
        obj = attributes.get(group_by_object)
        if obj is not None and not obj.startswith(("SYSTEM", "AMQ.MQEXPLORER")):
            obj = "%s:%s" % (qmname, obj)
            parsed.setdefault(obj, {})
            parsed[obj].update(attributes)

    def lookahead(iterable):
        """
        Pass through all values from the given iterable, augmented by the
        information if there are more values to come after the current one
        (True), or if it is the last value (False).
        """
        sentinel = object()
        previous = sentinel
        for value in iter(iterable):
            if previous is not sentinel:
                yield previous, True
            previous = value
        yield previous, False

    parsed: Dict[Any, Any] = {}
    attributes: Dict[Any, Any] = {}
    for (line,), has_more in lookahead(info):
        intro_line = re_intro.match(line)
        if intro_line:
            if attributes:
                record_group(qmname, attributes, parsed)  # type: ignore[has-type]
                attributes.clear()
            qmname = intro_line.group(1)
            qmstatus = intro_line.group(2)
            now = intro_line.group(3)
            parsed[qmname] = {"STATUS": qmstatus, "NOW": now}
            continue
        if re_group.match(line) or not has_more:
            if attributes:
                record_group(qmname, attributes, parsed)
                attributes.clear()
            continue
        if re_key.match(line):
            if re_second_column.match(line[39:]):
                first_half = line[:40]
                second_half = line[40:]
                record_attribute(first_half, attributes, parsed)
                record_attribute(second_half, attributes, parsed)
            else:
                record_attribute(line, attributes, parsed)
    return parsed


def is_ibm_mq_service_vanished(item, parsed) -> bool:
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
    raise MKCounterWrapped("Stale because queue manager %s" % qmgr_status)


def ibm_mq_check_version(actual_version, params, label):
    """
    >>> ibm_mq_check_version(
    ...    "2.0.0b4",
    ...     {"version": (("at_least", "2.0.0p2"), 2)},
    ...     "Doc test",
    ... )
    (2, 'Doc test: 2.0.0b4 (should be at least 2.0.0p2)')

    """

    def tokenize(version):
        _map_chars = {"p": 2, "b": 1, "i": 0}
        if not set("0123456789.pbi").issuperset(version):
            raise ValueError(version)
        return [
            _map_chars[g] if g in _map_chars else int(g)
            for g in re.findall(r"(\d+|[pbi]+)", version)
        ]

    info = "%s: %s" % (label, actual_version)
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
