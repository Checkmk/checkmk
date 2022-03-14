#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.agent_registration import UUIDLinkManager
from cmk.utils.paths import data_source_push_agent_dir, received_outputs_dir

from cmk.gui.exceptions import MKAuthException

_BASE = "/NO_SITE/check_mk/api/1.0"
_URL_LINK_UUID = _BASE + "/objects/host_config/example.com/actions/link_uuid/invoke"


@pytest.mark.usefixtures("with_host")
def test_openapi_host_link_uuid_400(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "put",
        _URL_LINK_UUID,
        params=json.dumps({"uuid": "abc-123"}),
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


@pytest.mark.usefixtures("with_host")
def test_link_with_uuid_401(
    mocker: MockerFixture,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    mocker.patch(
        "cmk.gui.plugins.openapi.endpoints.host_internal._check_host_editing_permissions",
        side_effect=MKAuthException("hands off this host"),
    )
    aut_user_auth_wsgi_app.call_method(
        "put",
        _URL_LINK_UUID,
        params=json.dumps({"uuid": "1409ac78-6548-4138-9285-12484409ddf2"}),
        status=401,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_host_link_uuid_204(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    uuid = UUID("1409ac78-6548-4138-9285-12484409ddf2")
    aut_user_auth_wsgi_app.call_method(
        "put",
        _URL_LINK_UUID,
        params=json.dumps({"uuid": str(uuid)}),
        status=204,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )
    assert (
        UUIDLinkManager(
            received_outputs_dir=received_outputs_dir,
            data_source_dir=data_source_push_agent_dir,
        ).get_uuid("example.com")
        == uuid
    )
