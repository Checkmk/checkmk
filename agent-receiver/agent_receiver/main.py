#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# register endpoints
from agent_receiver import endpoints  # pylint: disable=unused-import
from agent_receiver.apps_and_routers import AGENT_RECEIVER_APP, UUID_VALIDATION_ROUTER
from agent_receiver.log import configure_logger
from agent_receiver.site_context import log_path, site_name
from fastapi import FastAPI


def main_app() -> FastAPI:
    configure_logger(log_path())

    # this must happen *after* registering the endpoints
    AGENT_RECEIVER_APP.include_router(UUID_VALIDATION_ROUTER)

    main_app_ = FastAPI(
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    main_app_.mount(f"/{site_name()}/agent-receiver", AGENT_RECEIVER_APP)
    return main_app_
