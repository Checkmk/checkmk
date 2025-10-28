#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import StringTable

Section = Mapping[str, Mapping[str, Any]]

RE_INTRO = re.compile(r"^QMNAME\((.*)\)[\s]*STATUS\((.*?)\)[\s]*NOW\((.*)\)")
RE_GROUP = re.compile(r"^(AMQ\d+\w?:|CSQM\d+\w? !)")
RE_KEY = re.compile(r"([\s]*|CSQM\d+\w? ![A-Z0-9.]+[\s]+)([A-Z0-9]+\()")
RE_SECOND_COLUMN = re.compile(r"[A-Z]+\([^&]+\)$")
RE_KEY_VALUE = re.compile(r"([A-Z0-9]+)\(([^&]+)\)")


def parse_ibm_mq(string_table: StringTable, group_by_object: str) -> Section:
    def record_attribute(s, attributes):
        pair = RE_KEY_VALUE.search(s)
        if pair is None:
            return
        key = pair.group(1)
        value = pair.group(2).strip()
        # Do not overwrite existing attributes
        if key in attributes and str(value) in ("", "0", ",", "OFF"):
            return
        attributes[key] = value

    def record_group(qmname, attributes, parsed):
        obj = attributes.get(group_by_object)
        if obj is not None and not obj.startswith(("SYSTEM", "AMQ.MQEXPLORER")):
            obj = f"{qmname}:{obj}"
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

    parsed: dict[str, Any] = {}
    attributes: dict[str, Any] = {}
    qmname = ""  # TODO: Find some way to avoid setting this dummy value.
    for (line,), has_more in lookahead(string_table):
        intro_line = RE_INTRO.match(line)
        if intro_line:
            if attributes:
                record_group(qmname, attributes, parsed)  # type: ignore[has-type]  # noqa: F821 (undefined name)
                attributes.clear()
            qmname = intro_line.group(1)
            qmstatus = intro_line.group(2)
            now = intro_line.group(3)
            parsed[qmname] = {"STATUS": qmstatus, "NOW": now}
            continue

        if RE_GROUP.match(line) or not has_more:
            if attributes:
                record_group(qmname, attributes, parsed)  # noqa: F821 (undefined name)
                attributes.clear()
                # Remote group header do contain attribute(s)
                # do not go to next line now, test for attr

        if RE_KEY.match(line):
            if RE_SECOND_COLUMN.search(line[39:]):
                first_half = line[:40]
                second_half = line[40:]
                record_attribute(first_half, attributes)
                record_attribute(second_half, attributes)
            else:
                record_attribute(line, attributes)
    return parsed
