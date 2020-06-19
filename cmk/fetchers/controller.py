#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# Protocol: <header><payload>

import enum
import json
from pathlib import Path
from typing import Any, Union

from cmk.utils.paths import core_fetcher_config_dir

from . import TCPDataFetcher

#
# At the moment Protocol and API are opened to changes and input.
# TODO (ml): estimate possibility and efforts to serialize protocol im more intelligent manner:
# Ich bin gewöhnt eine Klasse für so was zu machen, die sich serialisiert mit `__bytes__` und
# sonst ganz normaler Accessoren hat, z.B. `inst.length -> int`, `inst.protocol -> str`, etc.
# Kann auch den Payload enthalten. Dann wird `length` automatisch vom Payload abgeleitet.
#


class Header:
    """Header is fixed size(5+8+9+9 = 31 bytes) string in format

      header: <ID>:<'SUCCESS'|'FAILURE'>:<HINT>:<SIZE>:
      ID   - 5 bytes protocol id, "base0" at the start
      HINT - 8 bytes string. Arbitrary data, usually some error info
      SIZE - 8 bytes string 0..9

    Example:
        "base0:SUCCESS:        :12345678:"

    """
    class State(str, enum.Enum):
        SUCCESS = "SUCCESS"
        FAILURE = "FAILURE"

    fmt = "{:<4}:{:<7}:{:<8}:{:<8}:"
    length = 31

    def __init__(self, name, state, hint, payload_length):
        # type: (str, Union[Header.State, str], str, int) -> None
        self.name = name
        self.state = Header.State(state) if isinstance(state, str) else state
        self.hint = hint
        self.payload_length = payload_length

    def __repr__(self):
        # type: () -> str
        return "%s(%r, %r, %r, %r)" % (
            type(self).__name__,
            self.name,
            self.state,
            self.hint,
            self.payload_length,
        )

    def __str__(self):
        # type: () -> str
        return Header.fmt.format(self.name, self.state, self.hint, self.payload_length)

    def __eq__(self, other):
        # type: (Any) -> bool
        return str(self) == str(other)

    def __hash__(self):
        # type: () -> int
        return hash(str(self))

    def __len__(self):
        # type: () -> int
        return Header.length

    @classmethod
    def from_network(cls, data):
        # type: (str) -> Header
        try:
            name, state, hint, payload_length = data[:Header.length].split(":")[:4]
            return cls(name, state, hint, int(payload_length, base=10))
        except ValueError as exc:
            raise ValueError(data) from exc

    def clone(self):
        # type: () -> Header
        return Header(self.name, self.state, self.hint, self.payload_length)


def supported_protocol_name():
    # type: () -> str
    return "fetch"


def make_success_answer(data):
    # type : (str) -> str
    return _make_success_header(length=len(data)) + data


def make_failure_answer(data, hint):
    # type : (str, str) -> str
    return _make_failure_header(length=len(data), hint=hint) + data


def _make_failure_header(length, hint):
    # type : (int, str) -> str
    return "{:<4}:FAILURE:{:<8}:{:<8}:".format(supported_protocol_name(), hint[:8], length)


def _make_success_header(length):
    # type : (int) -> str
    return "{:<4}:SUCCESS:{:<8}:{:<8}:".format(supported_protocol_name(), " ", length)


def run(serial, host, timeout):
    # type : (str, str, int) -> int
    # from var/check_mk/core/fetcher-config/[config-serial]/[host].mk
    json_content = read_json_file(serial=serial, host=host)

    # build fetcher in usual manner
    f = TCPDataFetcher.from_json(json.loads(json_content))
    if not f:
        print(make_failure_answer(json_content, "json"))
        return 1

    # print obtained data to the stdio
    # print(FetcherProtocol.make_success_answer(f.data());
    print(make_success_answer("used file:" + json_content))
    return 0


def read_json_file(serial, host):
    # type: (str, str) -> str
    json_file = build_json_file_path(serial=serial, host=host)
    return json_file.read_text(encoding="utf-8")


def build_json_file_path(serial, host):
    # type: (str, str) -> Path
    return Path("{}/{}/{}.mk".format(core_fetcher_config_dir, serial, host))
