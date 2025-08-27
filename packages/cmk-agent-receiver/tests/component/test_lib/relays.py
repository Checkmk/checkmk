#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from starlette.status import HTTP_200_OK

from .relay_proxy import RelayProxy


def register_relay(
    relay_id: str,
    relay_proxy: RelayProxy,
    expected_status_code: int = HTTP_200_OK,
) -> None:
    response = relay_proxy.register_relay(relay_id)
    assert response.status_code == expected_status_code, response.text


def unregister_relay(
    relay_id: str,
    relay_proxy: RelayProxy,
    expected_status_code: int = HTTP_200_OK,
) -> None:
    response = relay_proxy.unregister_relay(relay_id)
    assert response.status_code == expected_status_code, response.text
