#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from uuid import UUID

import pytest
from agent_receiver.checkmk_rest_api import link_host_with_uuid
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from pytest_mock import MockerFixture
from requests import Response


def test_link_host_with_uuid_unauthorized(
    mocker: MockerFixture,
    uuid: UUID,
) -> None:
    response = Response()
    response.status_code = 403
    response._content = (
        b'{"title": "You do not have the permission for agent pairing.", "status": 403}'
    )
    mocker.patch(
        "agent_receiver.checkmk_rest_api._forward_put",
        return_value=response,
    )
    with pytest.raises(HTTPException) as excpt_info:
        link_host_with_uuid(
            HTTPBasicCredentials(
                username="amdin",
                password="password",
            ),
            "some_host",
            uuid,
        )

    assert excpt_info.value.status_code == 403
    assert excpt_info.value.detail == "You do not have the permission for agent pairing."


def test_link_host_with_uuid_ok(
    mocker: MockerFixture,
    uuid: UUID,
) -> None:
    response = Response()
    response.status_code = 204
    mocker.patch(
        "agent_receiver.checkmk_rest_api._forward_put",
        return_value=response,
    )
    link_host_with_uuid(
        HTTPBasicCredentials(
            username="amdin",
            password="password",
        ),
        "some_host",
        uuid,
    )
