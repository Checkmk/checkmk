#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from fastapi import FastAPI

from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.lib.log import configure_logger
from cmk.agent_receiver.lib.middleware import B3RequestIDMiddleware
from cmk.ccc.version import edition
from cmk.licensing.basics.options import get_license_options

from .agent_receiver.app import create_app as create_ar_app
from .relay.app import create_app as create_relay_app
from .relay.app import lifespan as relay_lifespan


def main_app() -> FastAPI:
    config = get_config()
    relay_enabled = get_license_options(config.omd_root, edition(config.omd_root)).relay.enabled

    # Note: Defining the lifespan on a sub-app does not work as expected. So, it is defined on the
    # main app instead. It is only attached when the relay feature is enabled, since its sole
    # purpose is to schedule the initial relay config task.
    main_app_ = FastAPI(
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=relay_lifespan if relay_enabled else None,
    )

    # Configure logger on the main app level so it works with middleware
    configure_logger(config.log_path)

    # Add middleware to main app BEFORE mounting sub-apps
    main_app_.add_middleware(B3RequestIDMiddleware)

    # Mount the sub-app
    main_app_.mount(f"/{config.site_name}/relays", create_relay_app())
    main_app_.mount(f"/{config.site_name}/agent-receiver", create_ar_app())
    return main_app_
