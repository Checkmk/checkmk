#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus
from urllib.parse import urljoin
from uuid import UUID

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.utils.agent_registration import UUIDLinkManager
from cmk.utils.paths import (
    data_source_push_agent_dir,
    r4r_discoverable_dir,
    received_outputs_dir,
    uuid_lookup_dir,
)
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

_API_BASE = "/NO_SITE/check_mk/api/1.0/"
_HOST_CONFIG_INTERNAL_BASE = urljoin(_API_BASE, "objects/host_config_internal/")
_URL_REGISTER = urljoin(_HOST_CONFIG_INTERNAL_BASE, "example.com/actions/register/invoke")


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_ok(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    uuid = UUID("1409ac78-6548-4138-9285-12484409ddf2")
    response = aut_user_auth_wsgi_app.call_method(
        "put",
        _URL_REGISTER,
        params=json.dumps({"uuid": str(uuid)}),
        status=HTTPStatus.OK,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )
    assert set(response.json) == {"connection_mode"}
    assert (
        UUIDLinkManager(
            received_outputs_dir=received_outputs_dir,
            data_source_dir=data_source_push_agent_dir,
            r4r_discoverable_dir=r4r_discoverable_dir,
            uuid_lookup_dir=uuid_lookup_dir,
        ).uuid_store.get(HostName("example.com"))
        == uuid
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_missing(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.put(
        urljoin(_HOST_CONFIG_INTERNAL_BASE, "not-existant/actions/register/invoke"),
        params=json.dumps({"uuid": "1409ac78-6548-4138-9285-12484409ddf2"}),
        status=HTTPStatus.NOT_FOUND,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_bad_uuid(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.put(
        _URL_REGISTER,
        params=json.dumps({"uuid": "abc-123"}),
        status=HTTPStatus.BAD_REQUEST,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_cluster(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        urljoin(_API_BASE, "domain-types/host_config/collections/clusters"),
        params='{"host_name": "my-cluster", "folder": "/", "nodes": ["example.com"]}',
        status=HTTPStatus.OK,
        headers={"Accept": "application/json"},
        content_type='application/json; charset="utf-8"',
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        urljoin(_HOST_CONFIG_INTERNAL_BASE, "my-cluster/actions/register/invoke"),
        params=json.dumps({"uuid": "1409ac78-6548-4138-9285-12484409ddf2"}),
        status=HTTPStatus.METHOD_NOT_ALLOWED,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )
    assert "Cannot register cluster hosts" in resp.text


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_wrong_site(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        urljoin(_API_BASE, "domain-types/host_config/collections/all"),
        params='{"host_name": "my-host", "folder": "/", "attributes": {"site": "some-site"}}',
        status=HTTPStatus.BAD_REQUEST,
        headers={"Accept": "application/json"},
        content_type='application/json; charset="utf-8"',
    )
    assert any("attributes.site" in key for key in resp.json["fields"])
