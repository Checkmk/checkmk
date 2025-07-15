#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from urllib.parse import urljoin
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from tests.unit.cmk.web_test_app import WebTestAppForCMK

from cmk.ccc.hostaddress import HostName

from cmk.utils.agent_registration import UUIDLinkManager
from cmk.utils.paths import data_source_push_agent_dir, received_outputs_dir

from cmk.gui.exceptions import MKAuthException

_API_BASE = "/NO_SITE/check_mk/api/1.0/"
_HOST_CONFIG_INTERNAL_BASE = urljoin(_API_BASE, "objects/host_config_internal/")
_URL_LINK_UUID = urljoin(_HOST_CONFIG_INTERNAL_BASE, "example.com/actions/link_uuid/invoke")
_URL_REGISTER = urljoin(_HOST_CONFIG_INTERNAL_BASE, "example.com/actions/register/invoke")


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
        "cmk.gui.watolib.hosts_and_folders.PermissionChecker.need_permission",
        side_effect=MKAuthException("hands off this host"),
    )
    assert (
        aut_user_auth_wsgi_app.call_method(
            "put",
            _URL_LINK_UUID,
            params=json.dumps({"uuid": "1409ac78-6548-4138-9285-12484409ddf2"}),
            status=401,
            headers={"Accept": "application/json"},
            content_type="application/json; charset=utf-8",
        ).json_body["detail"]
        == "You do not have write access to the host example.com"
    )
    mocker.stopall()


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
        ).get_uuid(HostName("example.com"))
        == uuid
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_show_host_ok(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    assert aut_user_auth_wsgi_app.call_method(
        "get",
        urljoin(_HOST_CONFIG_INTERNAL_BASE, "heute"),
        status=200,
        headers={"Accept": "application/json"},
    ).json_body == {
        "site": "NO_SITE",
        "is_cluster": False,
    }


@pytest.mark.usefixtures("with_host")
def test_openapi_show_host_cluster_ok(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        urljoin(_API_BASE, "domain-types/host_config/collections/clusters"),
        params='{"host_name": "my-cluster", "folder": "/", "nodes": ["heute"]}',
        status=200,
        headers={"Accept": "application/json"},
        content_type='application/json; charset="utf-8"',
    )
    assert aut_user_auth_wsgi_app.call_method(
        "get",
        urljoin(_HOST_CONFIG_INTERNAL_BASE, "my-cluster"),
        status=200,
        headers={"Accept": "application/json"},
    ).json_body == {
        "site": "NO_SITE",
        "is_cluster": True,
    }


def test_openapi_show_host_missing(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "get",
        urljoin(_HOST_CONFIG_INTERNAL_BASE, "missing"),
        headers={"Accept": "application/json"},
        status=404,
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_show_host_401(
    mocker: MockerFixture,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    mocker.patch(
        "cmk.gui.watolib.hosts_and_folders.PermissionChecker.need_permission",
        side_effect=MKAuthException("hands off this host"),
    )
    assert (
        aut_user_auth_wsgi_app.call_method(
            "get",
            urljoin(_HOST_CONFIG_INTERNAL_BASE, "heute"),
            headers={"Accept": "application/json"},
            status=401,
        ).json_body["detail"]
        == "You do not have read access to the host heute"
    )
    mocker.stopall()


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_ok(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    uuid = UUID("1409ac78-6548-4138-9285-12484409ddf2")
    response = aut_user_auth_wsgi_app.call_method(
        "put",
        _URL_REGISTER,
        params=json.dumps({"uuid": str(uuid)}),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )
    assert set(response.json) == {"connection_mode"}
    assert (
        UUIDLinkManager(
            received_outputs_dir=received_outputs_dir,
            data_source_dir=data_source_push_agent_dir,
        ).get_uuid(HostName("example.com"))
        == uuid
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_missing(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.put(
        urljoin(_HOST_CONFIG_INTERNAL_BASE, "not-existant/actions/register/invoke"),
        params=json.dumps({"uuid": "1409ac78-6548-4138-9285-12484409ddf2"}),
        status=404,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_bad_uuid(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.put(
        _URL_REGISTER,
        params=json.dumps({"uuid": "abc-123"}),
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_host_register_cluster(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        urljoin(_API_BASE, "domain-types/host_config/collections/clusters"),
        params='{"host_name": "my-cluster", "folder": "/", "nodes": ["example.com"]}',
        status=200,
        headers={"Accept": "application/json"},
        content_type='application/json; charset="utf-8"',
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        urljoin(_HOST_CONFIG_INTERNAL_BASE, "my-cluster/actions/register/invoke"),
        params=json.dumps({"uuid": "1409ac78-6548-4138-9285-12484409ddf2"}),
        status=405,
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
        status=400,
        headers={"Accept": "application/json"},
        content_type='application/json; charset="utf-8"',
    )
    assert "site" in resp.json["fields"]["attributes"]
