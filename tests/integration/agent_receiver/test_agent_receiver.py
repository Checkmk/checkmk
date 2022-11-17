#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus

import requests

from tests.testlib.site import Site


def test_uuid_check_client_certificate(site: Site) -> None:
    agent_receiver_port = int(
        site.openapi.request(
            method="get",
            url="domain-types/internal/actions/discover-receiver/invoke",
        ).text
    )
    # try to acces the status endpoint by explicitly writing a fake UUID into the HTTP header
    uuid_ = uuid.uuid4()
    agent_receiver_response = requests.get(
        f"https://{site.http_address}:{agent_receiver_port}/{site.id}/agent-receiver/registration_status/{uuid_}",
        headers={"verified-uuid": str(uuid_)},
        verify=False,  # nosec
    )
    assert agent_receiver_response.status_code == HTTPStatus.BAD_REQUEST
    assert (
        "Verified client UUID (missing: no client certificate provided) does not match UUID in URL"
        in agent_receiver_response.json()["detail"]
    )
