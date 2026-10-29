#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from http import HTTPStatus
from typing import final

import httpx2

from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import SiteAuth


@final
class CheckmkAPIError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg


@final
class RelayNotFoundError(Exception):
    def __init__(self, relay_id: str) -> None:
        super().__init__(f"Relay {relay_id} not found")
        self.relay_id = relay_id


logger = logging.getLogger("agent-receiver")
default_num_fetchers = 13
default_log_level = "INFO"


@final
class SiteRelaysClient:
    def __init__(
        self,
        *,
        client: httpx2.Client,
        internal_client: httpx2.Client,
        siteid: str,
    ) -> None:
        self.client = client
        self.internal_client = internal_client
        self.siteid = siteid

    @classmethod
    def from_site(
        cls,
        *,
        site_url: str,
        internal_site_url: str,
        site_name: str,
    ) -> SiteRelaysClient:
        """Create SiteRelaysClient from site configuration."""
        # FIXME async client
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Checkmk Agent Receiver",
        }
        # FIXME: increased timeout due to flacky test test_tasks.py::test_max_tasks_per_relay
        timeout = 20
        client = httpx2.Client(base_url=site_url, headers=headers, timeout=timeout)
        internal_client = httpx2.Client(
            base_url=internal_site_url, headers=headers, timeout=timeout
        )
        return cls(
            client=client,
            internal_client=internal_client,
            siteid=site_name,
        )

    def add_relay(self, auth: SiteAuth, relay_id: RelayID, alias: str) -> RelayID:
        resp = self.internal_client.post(
            "/domain-types/relay/collections/all",
            auth=auth,
            json={
                "relay_id": str(relay_id),
                "alias": alias,
                "siteid": self.siteid,
                "num_fetchers": default_num_fetchers,
                "log_level": default_log_level,
            },
        )
        if resp.status_code != HTTPStatus.OK:
            logger.error(
                "could not register relay %(status_code)s : %(text)s",
                {"status_code": resp.status_code, "text": resp.text},
            )
            raise CheckmkAPIError(resp.text)
        assert relay_id == resp.json()["id"]
        return relay_id

    def relay_exists(self, auth: SiteAuth, relay_id: RelayID) -> bool:
        """Check if a relay exists by querying the REST API."""
        resp = self.client.get(f"/objects/relay/{relay_id}", auth=auth)
        if resp.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            raise CheckmkAPIError(resp.text)
        if resp.status_code == HTTPStatus.NOT_FOUND:
            return False
        if resp.status_code >= HTTPStatus.BAD_REQUEST:
            raise CheckmkAPIError(resp.text)
        return True
