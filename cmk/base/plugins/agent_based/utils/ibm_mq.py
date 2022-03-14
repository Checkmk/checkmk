#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import regex

from ..agent_based_api.v1.type_defs import StringTable

Section = Mapping[str, Mapping[str, Any]]


def parse_ibm_mq(string_table: StringTable, group_by_object: str) -> Section:
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

    parsed: Dict[str, Any] = {}
    attributes: Dict[str, Any] = {}
    for (line,), has_more in lookahead(string_table):
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
