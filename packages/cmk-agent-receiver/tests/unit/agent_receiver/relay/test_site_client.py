#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

import httpx2
import pytest
from pydantic import SecretStr

from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import SecretAuth
from cmk.agent_receiver.relay.lib.site_client import CheckmkAPIError, SiteRelaysClient

_AUTH = SecretAuth(SecretStr("Bearer test-token"))


def _site_answering(status: HTTPStatus) -> SiteRelaysClient:
    transport = httpx2.MockTransport(lambda _: httpx2.Response(status))
    return SiteRelaysClient(
        client=httpx2.AsyncClient(
            base_url="http://localhost/site/check_mk/api/1.0", transport=transport
        ),
        internal_client=httpx2.AsyncClient(
            base_url="http://localhost/site/check_mk/api/internal", transport=transport
        ),
        siteid="site",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "exists"), [(HTTPStatus.OK, True), (HTTPStatus.NOT_FOUND, False)]
)
async def test_relay_exists_as_the_site_answers(status: HTTPStatus, exists: bool) -> None:
    assert await _site_answering(status).relay_exists(_AUTH, RelayID("relay")) is exists


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [HTTPStatus.FORBIDDEN, HTTPStatus.INTERNAL_SERVER_ERROR])
async def test_relay_exists_raises_on_other_errors_of_the_site(status: HTTPStatus) -> None:
    with pytest.raises(CheckmkAPIError):
        await _site_answering(status).relay_exists(_AUTH, RelayID("relay"))
