#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi import FastAPI

# NOTE: The import below is a hack, we should register endpoints explicitly!
# TODO: The "bazel lint ..." calls for run_check_format() and run_check_ruff() don't agree on their findings. Why??
from . import endpoints  # noqa: F401, RUF100
from .apps_and_routers import AGENT_RECEIVER_APP, UUID_VALIDATION_ROUTER
from .log import configure_logger
from .site_context import log_path, site_name


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
