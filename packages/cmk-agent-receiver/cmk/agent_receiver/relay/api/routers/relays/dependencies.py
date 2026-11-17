#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, TypedDict

import fastapi

from cmk.agent_receiver.lib.config import Config, config_dependency
from cmk.agent_receiver.relay.api.dependencies.relay_config_repository import (
    get_relay_config_repository,
)
from cmk.agent_receiver.relay.api.dependencies.site_client import (
    get_site_relays_client,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import (
    ForwardMonitoringDataHandler,
    GetRelayStatusHandler,
    RefreshCertHandler,
    RegisterRelayHandler,
    StoreCrashReportHandler,
)
from cmk.agent_receiver.relay.lib.relay_config_repository import RelayConfigRepository
from cmk.agent_receiver.relay.lib.site_client import SiteRelaysClient


async def get_refresh_cert_handler(
    site_relays_client: Annotated[SiteRelaysClient, fastapi.Depends(get_site_relays_client)],
    relay_config_repository: Annotated[
        RelayConfigRepository, fastapi.Depends(get_relay_config_repository)
    ],
) -> RefreshCertHandler:
    return RefreshCertHandler(
        site_relays_client=site_relays_client, relay_config_repository=relay_config_repository
    )


async def get_register_relay_handler(
    site_relays_client: Annotated[SiteRelaysClient, fastapi.Depends(get_site_relays_client)],
) -> RegisterRelayHandler:
    return RegisterRelayHandler(site_relays_client=site_relays_client)


async def get_relay_status_handler(
    site_relays_client: Annotated[SiteRelaysClient, fastapi.Depends(get_site_relays_client)],
    relay_config_repository: Annotated[
        RelayConfigRepository, fastapi.Depends(get_relay_config_repository)
    ],
) -> GetRelayStatusHandler:
    return GetRelayStatusHandler(
        site_relays_client=site_relays_client, relay_config_repository=relay_config_repository
    )


class LifespanState(TypedDict):
    forward_monitoring_data_handler: ForwardMonitoringDataHandler


async def get_forward_monitoring_data_handler(
    request: fastapi.Request,
) -> ForwardMonitoringDataHandler:
    state: LifespanState = request.scope["state"]
    return state["forward_monitoring_data_handler"]


async def get_store_crash_report_handler(
    config: Annotated[Config, fastapi.Depends(config_dependency)],
) -> StoreCrashReportHandler:
    return StoreCrashReportHandler(
        crashes_base=config.crashes_dir, timeout=config.crash_extraction_timeout
    )
