#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.testlib.unit.rest_api_client import ClientRegistry


def test_list_views(clients: ClientRegistry) -> None:
    resp = clients.ViewClient.get_all()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert len(resp.json["value"]) > 0, "Expected at least one view to be returned"
