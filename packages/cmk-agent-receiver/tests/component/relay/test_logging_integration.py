#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.config import get_config


def test_log_lines_of_a_request_carry_its_trace_id(site_name: str, test_client: TestClient) -> None:
    trace_id = "test-logging-integration-12345"

    response = test_client.post(
        f"/{site_name}/relays/activate-config",
        headers={"x-trace-id": trace_id},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN, response.text
    for handler in logging.getLogger("agent-receiver").handlers:
        handler.flush()
    # The rejection of the non-local client is logged; other lines may stem from the startup.
    assert any(
        "activate-config" in line and trace_id in line
        for line in get_config().log_path.read_text().splitlines()
    )
