#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
)

#   .--Parse---------------------------------------------------------------.
#   |                      ____                                            |
#   |                     |  _ \ __ _ _ __ ___  ___                        |
#   |                     | |_) / _` | '__/ __|/ _ \                       |
#   |                     |  __/ (_| | |  \__ \  __/                       |
#   |                     |_|   \__,_|_|  |___/\___|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_jolokia_json_output(info: Sequence[Sequence[str]]) -> Iterable[Tuple[str, str, Any]]:
    for line in info:
        try:
            instance, mbean, raw_json_data = line
            yield instance, mbean, json.loads(raw_json_data)
        except ValueError:
            continue


def jolokia_mbean_attribute(attribute: object, mbean: str) -> str:
    tmp = mbean.split("%s=" % attribute, 1)[1]
    for delimiter in (",", "/"):
        tmp = tmp.split(delimiter, 1)[0]
    return tmp


def jolokia_basic_split(line: MutableSequence[str], expected_length: int) -> MutableSequence[str]:
    # line should consist of $expected_length tokens,
    # if there are more, we assume the second one
    # was split up by it's spaces.
    if len(line) == expected_length:
        return line
    if len(line) < expected_length:
        raise ValueError("Too few values: %r (expected >= %d)" % (line, expected_length))
    if expected_length < 2:
        raise NotImplementedError("use 'join' to create single token")
    tokens = line[:]
    while len(tokens) > expected_length:
        # len(tokens) is at least 3!
        tokens[1] += " %s" % tokens.pop(2)
    return tokens


def jolokoia_extract_opt(instance_raw: str) -> Tuple[str, MutableMapping[str, str], Sequence[str]]:
    if "," not in instance_raw:
        return instance_raw, {}, []

    instance, raw = instance_raw.split(",", 1)

    attr = {}
    pos = []
    for part in raw.split(","):
        if ":" in part:
            part = part.split(":", 1)[1]
        if "=" in part:
            key, val = part.split("=")
            attr[key] = val
        else:
            pos.append(part)

    return instance, attr, pos


#   .--Parse function------------------------------------------------------.
#   |  ____                        __                  _   _               |
#   | |  _ \ __ _ _ __ ___  ___   / _|_   _ _ __   ___| |_(_) ___  _ __    |
#   | | |_) / _` | '__/ __|/ _ \ | |_| | | | '_ \ / __| __| |/ _ \| '_ \   |
#   | |  __/ (_| | |  \__ \  __/ |  _| |_| | | | | (__| |_| | (_) | | | |  |
#   | |_|   \__,_|_|  |___/\___| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|  |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def jolokia_metrics_parse(info: Sequence[MutableSequence[str]]) -> Mapping[str, Mapping[str, Any]]:
    parsed: Dict[str, Dict[str, Any]] = {}
    for line in info:
        if len(line) > 1 and line[1] == "ERROR":
            continue

        try:
            inst_raw, var, value = jolokia_basic_split(line, 3)
        except ValueError:
            continue

        inst, attributes, positional = jolokoia_extract_opt(inst_raw)

        parsed.setdefault(inst, {})

        if "type" in attributes:
            bean_name = attributes.pop("name")
            bean_type = attributes.pop("type")
            # backwards compatibility
            bean_type = {"GarbageCollector": "gc", "ThreadPool": "tp"}.get(bean_type, bean_type)
            # maybe do this for all types?
            if bean_type == "tp":
                bean_name = bean_name.replace('"', "")

            bean = parsed[inst].setdefault(bean_type, {}).setdefault(bean_name, {})
            bean[var] = value
            bean.update(attributes)
        else:
            if positional:
                app = positional[0]
                app_dict = parsed[inst].setdefault("apps", {}).setdefault(app, {})
                if len(positional) > 1:
                    servlet = positional[1]
                    app_dict.setdefault("servlets", {}).setdefault(servlet, {})
                    app_dict["servlets"][servlet][var] = value
                else:
                    app_dict[var] = value
            else:
                parsed[inst][var] = value
    return parsed


# .
#   .--Generic inventory functions-----------------------------------------.
#   |                   ____                      _                        |
#   |                  / ___| ___ _ __   ___ _ __(_) ___                   |
#   |                 | |  _ / _ \ '_ \ / _ \ '__| |/ __|                  |
#   |                 | |_| |  __/ | | |  __/ |  | | (__                   |
#   |                  \____|\___|_| |_|\___|_|  |_|\___|                  |
#   |                                                                      |
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   |              __                  _   _                               |
#   |             / _|_   _ _ __   ___| |_(_) ___  _ __  ___               |
#   |            | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|              |
#   |            |  _| |_| | | | | (__| |_| | (_) | | | \__ \              |
#   |            |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_jolokia_metrics_apps(info: Any, what: str) -> Sequence[Tuple[str, Optional[str]]]:
    inv = []
    parsed = jolokia_metrics_parse(info)

    if what == "app_sess":
        levels: Optional[str] = "jolokia_metrics_app_sess_default_levels"
        needed_key = ["Sessions", "activeSessions"]
    elif what == "bea_app_sess":
        levels = "jolokia_metrics_app_sess_default_levels"
        needed_key = ["OpenSessionsCurrentCount"]
    elif what == "queue":
        needed_key = ["QueueLength"]
        levels = "jolokia_metrics_queue_default_levels"
    # Only works on BEA
    elif what == "bea_requests":
        needed_key = ["CompletedRequestCount"]
        levels = None
    elif what == "requests":
        needed_key = ["requestCount"]
        levels = None
    elif what == "threads":
        needed_key = ["StandbyThreadCount"]
        levels = None
    else:
        needed_key = ["Running", "stateName"]
        levels = None

    # this handles information from BEA, they stack one level
    # higher than the rest.
    if what == "bea_app_sess":
        for inst, vals in parsed.items():
            if vals is None:
                continue  # no data from agent

            for app, appstate in vals.get("apps", {}).items():
                if "servlets" in appstate:
                    for nk in needed_key:
                        for servlet in appstate["servlets"]:
                            if nk in appstate["servlets"][servlet]:
                                inv.append(("%s %s %s" % (inst, app, servlet), levels))
                                continue
    # This does the same for tomcat
    for inst, vals in parsed.items():
        if vals is None:
            continue  # no data from agent

        for app, appstate in vals.get("apps", {}).items():
            for nk in needed_key:
                if nk in appstate:
                    inv.append(("%s %s" % (inst, app), levels))
                    continue
    return inv
