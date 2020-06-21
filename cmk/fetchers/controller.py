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
# At the moment Protocol and API are opened to critic.
# Base structure and API are fixed
#


class Header:
    """Header is fixed size(6+8+9+9 = 32 bytes) string in format

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

    fmt = "{:<5}:{:<7}:{:<8}:{:<8}:"
    length = 32

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
        return Header.fmt.format(self.name[:5], self.state[:7], self.hint[:8], self.payload_length)

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
            # to simplify parsing we are using ':' as a splitter
            name, state, hint, payload_length = data[:Header.length].split(":")[:4]
            return cls(name, state, hint, int(payload_length, base=10))
        except ValueError as exc:
            raise ValueError(data) from exc

    def clone(self):
        # type: () -> Header
        return Header(self.name, self.state, self.hint, self.payload_length)

    @staticmethod
    def default_protocol_name():
        # type: () -> str
        return "fetch"


def make_success_answer(data):
    # type : (str) -> str
    return str(
        Header(name=Header.default_protocol_name(),
               state=Header.State.SUCCESS,
               hint=" ",
               payload_length=len(data))) + data


def make_failure_answer(data, hint):
    # type : (str, str) -> str
    return str(
        Header(name=Header.default_protocol_name(),
               state=Header.State.FAILURE,
               hint=hint,
               payload_length=len(data))) + data


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
