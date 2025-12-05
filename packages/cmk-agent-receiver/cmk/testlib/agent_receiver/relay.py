#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import uuid
from http import HTTPStatus

import httpx

from cmk.agent_receiver.relay.lib.relays_repository import CheckmkAPIError
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import SiteAuth

logger = logging.getLogger(__name__)


def random_relay_id() -> RelayID:
    """Generates a random RelayID for testing purposes."""
    return RelayID(str(uuid.uuid4()))


def site_has_relay(client: httpx.Client, relay_id: RelayID, auth: SiteAuth) -> bool:
    resp = client.get(url=f"/objects/relay/{relay_id}", auth=auth)
    if resp.status_code == HTTPStatus.NOT_FOUND:
        return False
    if resp.status_code == HTTPStatus.OK:
        return True
    logger.error("could not check if relay exists %s : %s", resp.status_code, resp.text)
    raise CheckmkAPIError(resp.text)
