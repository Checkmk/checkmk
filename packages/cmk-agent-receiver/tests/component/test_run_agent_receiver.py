#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .test_lib.relay_proxy import RelayProxy


def test_health_check(relay_proxy: RelayProxy) -> None:
    response = relay_proxy.client.get(f"/{relay_proxy.site_name}/agent-receiver/openapi.json")
    assert response.status_code == 200
