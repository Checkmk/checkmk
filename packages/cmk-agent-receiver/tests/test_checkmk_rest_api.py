#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from pydantic import UUID4
from pytest_mock import MockerFixture
from requests import Response

from cmk.agent_receiver.checkmk_rest_api import link_host_with_uuid


def test_link_host_with_uuid_unauthorized(
    mocker: MockerFixture,
    uuid: UUID4,
) -> None:
    response = Response()
    response.status_code = 403
    response._content = (  # noqa: SLF001
        b'{"title": "You do not have the permission for agent pairing.", "status": 403}'
    )
    mocker.patch(
        "cmk.agent_receiver.checkmk_rest_api._forward_put",
        return_value=response,
    )
    with pytest.raises(HTTPException) as excpt_info:
        link_host_with_uuid(
            "some log message",
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
    uuid: UUID4,
) -> None:
    response = Response()
    response.status_code = 204
    mocker.patch(
        "cmk.agent_receiver.checkmk_rest_api._forward_put",
        return_value=response,
    )
    link_host_with_uuid(
        "some log message",
        HTTPBasicCredentials(
            username="amdin",
            password="password",
        ),
        "some_host",
        uuid,
    )
