#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

import pytest

from tests.testlib import SpecialAgent


@pytest.fixture(name="agent", scope="module")
def _get_agent() -> SpecialAgent:
    return SpecialAgent("agent_elasticsearch")


def test_agent_elasticsearch_arguments_cert_check(agent: SpecialAgent) -> None:

    params: dict[str, str | Sequence[str] | bool] = {
        "hosts": "testhost",
        "protocol": "https",
        "infos": ["cluster_health", "nodestats", "stats"],
    }
    assert "--no-cert-check" not in agent.argument_func(params, "testhost", "1.2.3.4")

    params["no-cert-check"] = True
    assert "--no-cert-check" in agent.argument_func(params, "testhost", "1.2.3.4")


def test_agent_elasticsearch_arguments_password_store(agent: SpecialAgent) -> None:

    params = {
        "hosts": "testhost",
        "protocol": "https",
        "infos": ["cluster_health", "nodestats", "stats"],
        "user": "user",
        "password": ("password", "pass"),
    }
    assert agent.argument_func(params, "testhost", "1.2.3.4") == [
        "-P",
        "https",
        "-m",
        " ".join(params["infos"]),
        "-u",
        "user",
        "-s",
        "pass",
    ] + list(params["hosts"])
