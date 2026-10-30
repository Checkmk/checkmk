#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from pydantic import SecretStr

from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.relay.api.routers.relays.handlers.cert_retriever import get_certificates
from cmk.agent_receiver.relay.lib.relay_config_repository import RelayConfigRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, RemoteSiteError
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth, parse_authorization, SiteAuth
from cmk.agent_receiver.relay.lib.site_client import (
    RelayNotFoundError,
    SiteRelaysClient,
)
from cmk.relay_protocols import relays as relay_protocols
from cmk.relay_protocols.relays import RelayState


@dataclasses.dataclass
class RegisterRelayHandler:
    site_relays_client: SiteRelaysClient

    async def process(
        self, authorization: SecretStr, request: relay_protocols.RelayRegistrationRequest
    ) -> relay_protocols.RelayRegistrationResponse:
        if get_config().is_remote_site:
            raise RemoteSiteError
        relay_id = RelayID(request.relay_id)
        # Important: First authenticate
        auth = parse_authorization(authorization)

        certificates = get_certificates(request.csr, relay_id)

        # before relay registration
        await self.site_relays_client.add_relay(auth, relay_id, request.alias)

        return relay_protocols.RelayRegistrationResponse(
            relay_id=relay_id,
            root_cert=certificates.root_cert,
            client_cert=certificates.client_cert,
        )


@dataclasses.dataclass
class RefreshCertHandler:
    site_relays_client: SiteRelaysClient
    relay_config_repository: RelayConfigRepository

    async def process(
        self, relay_id: RelayID, request: relay_protocols.RelayRefreshCertRequest
    ) -> relay_protocols.RelayRefreshCertResponse:
        auth = InternalAuth()
        # Allow cert refresh for any relay known to the agent-receiver, including
        # relays in PENDING_DELETION (deleted from the site but change not yet activated).
        # get_relay_state() raises RelayNotFoundError if the relay is unknown everywhere.
        await get_relay_state(self.site_relays_client, self.relay_config_repository, auth, relay_id)
        certificates = get_certificates(request.csr, relay_id)
        return relay_protocols.RelayRefreshCertResponse(
            root_cert=certificates.root_cert,
            client_cert=certificates.client_cert,
        )


@dataclasses.dataclass
class GetRelayStatusHandler:
    site_relays_client: SiteRelaysClient
    relay_config_repository: RelayConfigRepository

    async def process(self, relay_id: RelayID) -> relay_protocols.RelayStatusResponse:
        """Get relay status.

        Returns:
            RelayStatusResponse with relay_id and state

        Raises:
            RelayNotFoundError: If the relay does not exist anywhere
            CheckmkAPIError: If there is an API error
        """
        auth = InternalAuth()
        state = await get_relay_state(
            self.site_relays_client, self.relay_config_repository, auth, relay_id
        )
        return relay_protocols.RelayStatusResponse(relay_id=relay_id, state=state)


async def get_relay_state(
    site_relays_client: SiteRelaysClient,
    relay_config_repository: RelayConfigRepository,
    auth: SiteAuth,
    relay_id: RelayID,
) -> RelayState:
    """Get relay state by comparing local config and CMK API.

    Returns:
        RelayState indicating the current state of the relay

    Raises:
        RelayNotFoundError: If the relay does not exist anywhere
        CheckmkAPIError: If there is an API error
    """
    relay_in_config = relay_config_repository.has_config(relay_id)
    relay_in_api = await site_relays_client.relay_exists(auth, relay_id)

    if not relay_in_api and not relay_in_config:
        raise RelayNotFoundError(relay_id)
    if relay_in_api and not relay_in_config:
        return RelayState.PENDING_ACTIVATION
    if not relay_in_api and relay_in_config:
        return RelayState.PENDING_DELETION
    return RelayState.CONFIGURED
