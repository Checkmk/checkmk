#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.relay_protocols.tasks import AdHocActiveCheckTask, TaskCreateRequest, TaskResponse


def test_fields_and_default_timeout() -> None:
    task = AdHocActiveCheckTask(host="myhost", command="check_icmp 1.2.3.4")
    assert task.host == "myhost"
    assert task.command == "check_icmp 1.2.3.4"
    assert task.timeout == 60.0
    assert task.type == "AD_HOC_ACTIVE_CHECK"


def test_discriminated_in_create_request() -> None:
    request = TaskCreateRequest.model_validate(
        {"spec": {"type": "AD_HOC_ACTIVE_CHECK", "host": "h", "command": "c"}}
    )
    assert isinstance(request.spec, AdHocActiveCheckTask)


def test_discriminated_in_task_response() -> None:
    response = TaskResponse.model_validate(
        {
            "spec": {"type": "AD_HOC_ACTIVE_CHECK", "host": "h", "command": "c"},
            "status": "PENDING",
            "result_type": None,
            "result_payload": None,
            "creation_timestamp": "2026-01-01T00:00:00",
            "update_timestamp": "2026-01-01T00:00:00",
            "id": "task-1",
        }
    )
    assert isinstance(response.spec, AdHocActiveCheckTask)
