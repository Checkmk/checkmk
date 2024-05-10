#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

import cmk.plugins.jenkins.agent_based.jenkins_instance as ji


@pytest.fixture(scope="module", name="section")
def _section() -> ji.JenkinsInstance:
    return ji.parse_jenkins_instance(
        [
            [
                """
                {"quietingDown": false, "nodeDescription": "the master Jenkins node", "numExecutors": 10, "mode": "NORMAL", "_class": "hudson.model.Hudson", "useSecurity": true}
                """
            ]
        ]
    )


def test_discovery(section: ji.JenkinsInstance) -> None:
    assert list(ji.inventory_jenkins_instance(section)) == [Service()]


def test_check_jenkins_instance(section: ji.JenkinsInstance) -> None:
    assert list(ji.check_jenkins_instance({}, section)) == [
        Result(state=State.OK, summary="Description: The Master Jenkins Node"),
        Result(state=State.OK, summary="Quieting Down: no"),
        Result(state=State.OK, summary="Security used: yes"),
    ]
