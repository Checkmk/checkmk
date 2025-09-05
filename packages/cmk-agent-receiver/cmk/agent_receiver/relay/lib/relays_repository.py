#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from http import HTTPStatus
from typing import final

import httpx
from pydantic import SecretStr

from cmk.agent_receiver.relay.lib.shared_types import RelayID


@final
class CheckmkAPIError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg


logger = logging.getLogger("agent-receiver")


@final
class RelaysRepository:
    def __init__(self, client: httpx.Client, siteid: str) -> None:
        self.client = client
        self.siteid = siteid

    @classmethod
    def from_site(cls, site_url: str, site_name: str) -> "RelaysRepository":
        """Create RelaysRepository from site configuration."""
        base_url = f"{site_url}/{site_name}/check_mk/api/1.0"
        # FIXME async client
        client = httpx.Client(
            base_url=base_url,
            headers={"Content-Type": "application/json"},
        )
        siteid = os.environ["OMD_SITE"]
        return cls(client, siteid)

    def add_relay(self, authorization: SecretStr, alias: str) -> RelayID:
        resp = self.client.post(
            "/domain-types/relay/collections/all",
            headers={"Authorization": authorization.get_secret_value()},
            json={"alias": alias, "siteid": self.siteid},
        )
        if resp.status_code != HTTPStatus.OK:
            logger.error("could not register relay %s : %s", resp.status_code, resp.text)
            raise CheckmkAPIError(resp.text)
        return resp.json()["id"]

    def list_relays(self, authorization: SecretStr) -> list[RelayID]:
        resp = self.client.get(
            "/domain-types/relay/collections/all",
            headers={"Authorization": authorization.get_secret_value()},
        )
        if resp.status_code != HTTPStatus.OK:
            logger.error("could not list relays %s : %s", resp.status_code, resp.text)
            raise CheckmkAPIError(resp.text)
        values = resp.json()["value"]
        return [v["id"] for v in values]

    def has_relay(self, relay_id: RelayID, authorization: SecretStr) -> bool:
        resp = self.client.get(
            url=f"objects/relay/{relay_id}",
            headers={"Authorization": authorization.get_secret_value()},
        )
        if resp.status_code == HTTPStatus.NOT_FOUND:
            return False
        if resp.status_code == HTTPStatus.OK:
            return True
        logger.error("could not check if relay exists %s : %s", resp.status_code, resp.text)
        raise CheckmkAPIError(resp.text)

    def remove_relay(self, relay_id: RelayID, authorization: SecretStr) -> None:
        resp = self.client.delete(
            url=f"objects/relay/{relay_id}",
            headers={"Authorization": authorization.get_secret_value()},
        )
        if resp.status_code != HTTPStatus.NO_CONTENT:
            logger.error("could not delete relay %s : %s", resp.status_code, resp.text)
            raise CheckmkAPIError(resp.text)
