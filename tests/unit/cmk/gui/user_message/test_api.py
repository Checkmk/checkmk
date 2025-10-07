#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.unit.rest_api_client import ClientRegistry


# TODO: proper tests for acknowledge and delete should be added once a create endpoint is available
def test_acknowledge_non_existing_message(clients: ClientRegistry) -> None:
    resp = clients.UserMessage.acknowledge(message_id="non_existing", expect_ok=False)

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.body!r}"


def test_delete_non_existing_message(clients: ClientRegistry) -> None:
    resp = clients.UserMessage.delete(message_id="non_existing", expect_ok=False)

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.body!r}"
