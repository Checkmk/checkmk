#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from http import HTTPStatus
from typing import final

import httpx
from pydantic import SecretStr

from cmk.agent_receiver.relay.lib.shared_types import RelayID

logger = logging.getLogger("agent-receiver")


@final
class RelaysRepository:
    def __init__(self, site_url: str, site_name: str) -> None:
        base_url = f"{site_url}/{site_name}/check_mk/api/1.0"
        # FIXME async client
        self.client = httpx.Client(
            base_url=base_url,
            headers={"Content-Type": "application/json"},
        )

    def add_relay(self, authorization: SecretStr) -> RelayID:
        resp = self.client.post(
            "/domain-types/relay/collections/all",
            headers={"Authorization": authorization.get_secret_value()},
        )
        if resp.status_code != HTTPStatus.OK:
            logger.error("could not register relay %s : %s", resp.status_code, resp.text)
            raise RuntimeError()  # FIXME
        return resp.json()["id"]

    def list_relays(self, authorization: SecretStr) -> list[RelayID]:
        resp = self.client.get(
            "/domain-types/relay/collections/all",
            headers={"Authorization": authorization.get_secret_value()},
        )
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError()  # FIXME
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
        raise RuntimeError

    def remove_relay(self, relay_id: RelayID, authorization: SecretStr) -> None:
        resp = self.client.delete(
            url=f"objects/relay/{relay_id}",
            headers={"Authorization": authorization.get_secret_value()},
        )
        if resp.status_code != HTTPStatus.NO_CONTENT:
            raise RuntimeError
