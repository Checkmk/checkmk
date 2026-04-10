#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.jenkins.agent_based.jenkins_instance import (
    check_jenkins_instance,
    discover_jenkins_instance,
    parse_jenkins_instance,
)


def test_parse_jenkins_instance() -> None:
    payload = _build_test_payload()
    string_table = [[json.dumps(payload)]]

    value = parse_jenkins_instance(string_table)
    expected = {
        "_class": "hudson.model.Hudson",
        "mode": "NORMAL",
        "nodeDescription": "the master Jenkins node",
        "numExecutors": 10,
        "quietingDown": False,
        "useSecurity": True,
    }

    assert value == expected


def test_discovery_jenkins_instance() -> None:
    payload = _build_test_payload()
    string_table = [[json.dumps(payload)]]
    section = parse_jenkins_instance(string_table)

    value = list(discover_jenkins_instance(section))
    expected = [Service()]

    assert value == expected


def test_check_jenkins_instance() -> None:
    payload = _build_test_payload()
    string_table = [[json.dumps(payload)]]
    section = parse_jenkins_instance(string_table)

    value = list(check_jenkins_instance({}, section))
    expected = [
        Result(state=State.OK, summary="Description: The Master Jenkins Node"),
        Result(state=State.OK, summary="Quieting Down: no"),
        Result(state=State.OK, summary="Security used: yes"),
    ]

    assert value == expected


def _build_test_payload(**kwargs: object) -> Mapping[str, object]:
    defaults = {
        "quietingDown": False,
        "nodeDescription": "the master Jenkins node",
        "numExecutors": 10,
        "mode": "NORMAL",
        "_class": "hudson.model.Hudson",
        "useSecurity": True,
    }
    return {**defaults, **kwargs}
