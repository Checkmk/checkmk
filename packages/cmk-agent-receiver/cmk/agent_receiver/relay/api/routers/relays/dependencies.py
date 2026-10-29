#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import concurrent.futures
from functools import cache
from typing import Annotated

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


def get_refresh_cert_handler(
    site_relays_client: Annotated[SiteRelaysClient, fastapi.Depends(get_site_relays_client)],
    relay_config_repository: Annotated[
        RelayConfigRepository, fastapi.Depends(get_relay_config_repository)
    ],
) -> RefreshCertHandler:
    return RefreshCertHandler(
        site_relays_client=site_relays_client, relay_config_repository=relay_config_repository
    )


def get_register_relay_handler(
    site_relays_client: Annotated[SiteRelaysClient, fastapi.Depends(get_site_relays_client)],
) -> RegisterRelayHandler:
    return RegisterRelayHandler(site_relays_client=site_relays_client)


def get_relay_status_handler(
    site_relays_client: Annotated[SiteRelaysClient, fastapi.Depends(get_site_relays_client)],
    relay_config_repository: Annotated[
        RelayConfigRepository, fastapi.Depends(get_relay_config_repository)
    ],
) -> GetRelayStatusHandler:
    return GetRelayStatusHandler(
        site_relays_client=site_relays_client, relay_config_repository=relay_config_repository
    )


async def get_forward_monitoring_data_handler(
    config: Annotated[Config, fastapi.Depends(config_dependency)],
) -> ForwardMonitoringDataHandler:
    return ForwardMonitoringDataHandler(
        data_socket=config.raw_data_socket, socket_timeout=config.socket_timeout
    )


@cache
def get_crash_extraction_executor() -> concurrent.futures.ThreadPoolExecutor:
    # Own threads: the default executor is shared with the credential lookup in
    # lib.auth, so a burst of uploads would delay every other request.
    return concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="crash-extract")


def get_store_crash_report_handler(
    config: Annotated[Config, fastapi.Depends(config_dependency)],
    executor: Annotated[
        concurrent.futures.Executor, fastapi.Depends(get_crash_extraction_executor)
    ],
) -> StoreCrashReportHandler:
    return StoreCrashReportHandler(
        crashes_base=config.crashes_dir,
        executor=executor,
        timeout=config.crash_extraction_timeout,
    )
