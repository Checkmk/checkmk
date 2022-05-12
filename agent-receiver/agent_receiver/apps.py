#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from agent_receiver.certificates import CertValidationRoute
from agent_receiver.log import configure_logger
from agent_receiver.site_context import log_path, site_name
from fastapi import APIRouter, FastAPI

agent_receiver_app = FastAPI(title="Checkmk Agent Receiver")
cert_validation_router = APIRouter(route_class=CertValidationRoute)


def main_app() -> FastAPI:
    configure_logger(log_path())

    # register endpoints
    from agent_receiver import endpoints  # pylint: disable=unused-import

    # this must happen *after* registering the endpoints
    agent_receiver_app.include_router(cert_validation_router)

    main_app_ = FastAPI(
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    main_app_.mount(f"/{site_name()}/agent-receiver", agent_receiver_app)
    return main_app_
