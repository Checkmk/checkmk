#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from http import HTTPStatus
from pathlib import Path
from typing import final

import httpx

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
class RelaysRepository:
    def __init__(self, client: httpx.Client, siteid: str, helper_config_dir: Path) -> None:
        self.client = client
        self.siteid = siteid
        self.helper_config_dir = helper_config_dir

    @classmethod
    def from_site(
        cls, site_url: str, site_name: str, helper_config_dir: Path
    ) -> "RelaysRepository":
        """Create RelaysRepository from site configuration."""
        # FIXME async client
        client = httpx.Client(
            base_url=site_url,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Checkmk Agent Receiver",
            },
            timeout=20,  # FIXME: increased timeout due to flacky test test_tasks.py::test_max_tasks_per_relay
        )
        return cls(client, site_name, helper_config_dir)

    def add_relay(self, auth: SiteAuth, relay_id: RelayID, alias: str) -> RelayID:
        resp = self.client.post(
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
            logger.error("could not register relay %s : %s", resp.status_code, resp.text)
            raise CheckmkAPIError(resp.text)
        assert relay_id == resp.json()["id"]
        return relay_id

    def get_all_relay_ids(self) -> list[RelayID]:
        latest = self.helper_config_dir / "latest/relays"
        try:
            dirs = next(latest.walk())[1]
            return [RelayID(x) for x in dirs]
        except StopIteration:
            # The folder does not exist
            return []

    def relay_exists(self, auth: SiteAuth, relay_id: RelayID) -> bool:
        """Check if a relay exists by querying the REST API."""
        resp = self.client.get(f"/objects/relay/{relay_id}", auth=auth)
        if resp.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            raise CheckmkAPIError(resp.text)
        elif resp.status_code == HTTPStatus.NOT_FOUND:
            return False
        elif resp.status_code >= HTTPStatus.BAD_REQUEST:
            raise CheckmkAPIError(resp.text)
        return True
