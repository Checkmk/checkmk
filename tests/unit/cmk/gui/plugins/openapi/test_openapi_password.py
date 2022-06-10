# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import password_store, version
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_password(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/password/collections/all",
        params=json.dumps(
            {
                "ident": "foo",
                "title": "foobar",
                "owner": "admin",
                "password": "tt",
                "shared": ["all"],
                "customer": "global",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/password/fooz",
        params=json.dumps({"title": "foobu", "comment": "Something but nothing random"}),
        status=404,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/password/foo",
        params=json.dumps({"title": "foobu", "comment": "Something but nothing random"}),
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/password/foo",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json["extensions"] == {
        "comment": "Something but nothing random",
        "documentation_url": "",
        "owned_by": None,
        "shared": ["all"],
        "customer": "global",
    }


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_password_admin(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/password/collections/all",
        params=json.dumps(
            {
                "ident": "test",
                "title": "Checkmk",
                "owner": "admin",
                "password": "tt",
                "shared": [],
                "customer": "provider",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/password/test",
        headers={"Accept": "application/json"},
        status=200,
    )


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_password_customer(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/password/collections/all",
        params=json.dumps(
            {
                "ident": "test",
                "title": "Checkmk",
                "owner": "admin",
                "password": "tt",
                "shared": [],
                "customer": "provider",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["customer"] == "provider"

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/password/test",
        params=json.dumps(
            {
                "customer": "global",
            }
        ),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/password/test",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json_body["extensions"]["customer"] == "global"


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_password_delete(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/password/collections/all",
        params=json.dumps(
            {
                "ident": "foo",
                "title": "foobar",
                "owner": "admin",
                "password": "tt",
                "shared": ["all"],
                "customer": "global",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/password/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp.json_body["value"]) == 1

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/password/nothing",
        headers={"Accept": "application/json"},
        status=404,
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/password/foo",
        headers={"Accept": "application/json"},
        status=204,
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "get", base + "/objects/password/foo", headers={"Accept": "application/json"}, status=404
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/password/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp.json_body["value"]) == 0


def test_password_with_newlines(
    aut_user_auth_wsgi_app: WebTestAppForCMK, mock_livestatus: MockLiveStatusConnection
):
    base = "/NO_SITE/check_mk/api/1.0"

    credentials_with_newlines = """{
        "type": "service_account",
        "project_id": "myCoolProject",
        "private_key_id": "foobar",
        "private_key": "I\\nhave\\nnewlines\\n",
        "client_email": "me@example.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/me@example.com"
    }"""

    def create_host(hostname: str):
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/host_config/collections/all?bake_agent=False",
            content_type="application/json",
            headers={"Accept": "application/json"},
            params=json.dumps(
                {
                    "folder": "/",
                    "host_name": hostname,
                    "attributes": {
                        "tag_address_family": "no-ip",
                        "tag_agent": "special-agents",
                    },
                }
            ),
            status=200,
        )

    def create_gcp_rule():
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/rule/collections/all",
            content_type="application/json",
            headers={"Accept": "application/json"},
            params=json.dumps(
                {
                    "ruleset": "special_agents:gcp",
                    "folder": "/",
                    "properties": {"disabled": False},
                    "value_raw": repr(
                        {
                            "credentials": ("password", credentials_with_newlines),
                            "project": "tribe29-check-development",
                            "services": [
                                #                    "gcs",
                                #                    "gce",
                                "cloud_run",
                                #                    "cloud_functions",
                                #                    "cloud_sql",
                                #                    "filestore",
                                #                    "redis",
                            ],
                        }
                    ),
                    "conditions": {"host_name": {"match_on": ["gcp"], "operator": "one_of"}},
                }
            ),
            status=200,
        )

    def activate_changes():
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            headers={"Accept": "application/json"},
            content_type="application/json",
            params=json.dumps(
                {"redirect": False, "sites": ["NO_SITE"], "force_foreign_changes": True}
            ),
            status=200,
        )

    def create_password():
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/password/collections/all",
            content_type="application/json",
            headers={"Accept": "application/json"},
            params=json.dumps(
                {
                    "customer": "provider",
                    "ident": "gcp",
                    "title": "gcp",
                    "comment": "Kommentar",
                    "documentation_url": "localhost",
                    "password": credentials_with_newlines,
                    "owner": "admin",
                    "shared": ["all"],
                }
            ),
            status=200,
        )

    with mock_livestatus():
        create_host("gcp")

        create_password()
        create_gcp_rule()
        activate_changes()

    password_store.load()  # see if it loads correctly
