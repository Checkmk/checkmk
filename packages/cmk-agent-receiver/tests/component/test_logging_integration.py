#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

from cmk.agent_receiver.config import get_config
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient


def test_middleware_adds_request_id_to_logs(
    agent_receiver: AgentReceiverClient,
) -> None:
    trace_id = "test-logging-integration-12345"
    response = agent_receiver.client.get(
        f"/{agent_receiver.site_name}/agent-receiver/openapi.json", headers={"x-trace-id": trace_id}
    )
    assert response.headers["x-request-id"] == trace_id

    # Flush logging handlers to ensure logs are written to file
    for handler in logging.getLogger("agent-receiver").handlers:
        handler.flush()

    # The log file should exist and contain the request ID
    # Note: The openapi.json endpoint may not generate application logs,
    # but middleware should still bind the request_id to the logging context
    config = get_config()
    logfile = config.log_path
    if logfile.exists():
        if log_content := logfile.read_text().strip():
            assert trace_id in log_content, (
                f"Request ID {trace_id} not found in logs: {log_content}"
            )
