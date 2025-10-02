#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient


def test_health_check(agent_receiver: AgentReceiverClient) -> None:
    response = agent_receiver.client.get(f"/{agent_receiver.site_name}/agent-receiver/openapi.json")
    assert response.status_code == 200
