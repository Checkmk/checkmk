#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from http import HTTPStatus

import httpx

from cmk.agent_receiver.relay.lib.shared_types import RelayID

logger = logging.getLogger("agent-receiver")


class RelaysRepository:
    def __init__(self, site_url: str, site_name: str) -> None:
        base_url = f"{site_url}/{site_name}/check_mk/api/1.0"
        # FIXME async client
        self.client = httpx.Client(
            base_url=base_url,
        )

    def add_relay(self) -> RelayID:
        resp = self.client.post(
            "/domain-types/relay/collections/all",
        )
        if resp.status_code != HTTPStatus.OK:
            logger.error("could not register relay %s : %s", resp.status_code, resp.text)
            raise RuntimeError()  # FIXME
        return resp.json()["id"]

    def list_relays(self) -> list[RelayID]:
        resp = self.client.get(
            "/domain-types/relay/collections/all",
        )
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError()  # FIXME
        values = resp.json()["value"]
        return [v["id"] for v in values]

    def has_relay(self, relay_id: RelayID) -> bool:
        resp = self.client.get(url=f"objects/relay/{relay_id}")
        if resp.status_code == HTTPStatus.NOT_FOUND:
            return False
        if resp.status_code == HTTPStatus.OK:
            return True
        raise RuntimeError

    def remove_relay(self, relay_id: RelayID) -> None:
        resp = self.client.delete(url=f"objects/relay/{relay_id}")
        if resp.status_code != HTTPStatus.NO_CONTENT:
            raise RuntimeError
