#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from http import HTTPStatus

import httpx

from scripts.gerrit_api.client import GerritClient


def test_non_ascii_credentials_are_sent_utf8_encoded() -> None:
    sent: list[httpx.Request] = []

    def gerrit(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(HTTPStatus.OK)

    client = GerritClient("jürgen", "s€cret", transport=httpx.MockTransport(gerrit))

    client.get(f"{GerritClient.GERRIT_URL}/accounts/self")

    scheme, _, encoded = sent[0].headers["Authorization"].partition(" ")
    assert (scheme, base64.b64decode(encoded).decode("utf-8")) == ("Basic", "jürgen:s€cret")
