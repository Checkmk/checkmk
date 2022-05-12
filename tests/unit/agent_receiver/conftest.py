#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from uuid import UUID, uuid4

import pytest
from agent_receiver import site_context
from agent_receiver.apps import agent_receiver_app, main_app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_site_context() -> None:
    site_context.agent_output_dir().mkdir(parents=True)
    site_context.r4r_dir().mkdir(parents=True)
    site_context.log_path().parent.mkdir(parents=True)


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    main_app()
    return TestClient(agent_receiver_app)


@pytest.fixture(name="uuid")
def fixture_uuid() -> UUID:
    return uuid4()
