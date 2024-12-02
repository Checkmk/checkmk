#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.rest_api_client import ClientRegistry

from cmk.ccc import version

from cmk.utils import password_store, paths

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls", "mock_password_file_regeneration")
def test_openapi_password(clients: ClientRegistry) -> None:
    clients.Password.create(
        ident="invalid%$",
        title="foobar",
        password="tt",
        shared=["all"],
        editable_by="admin",
        customer="global",
        expect_ok=False,
    ).assert_status_code(400)

    clients.Password.create(
        ident="foo:invalid",
        title="foobar",
        password="tt",
        shared=["all"],
        editable_by="admin",
        customer="global",
        expect_ok=False,
    ).assert_status_code(400)

    clients.Password.create(
        ident="foo",
        title="foobar",
        password="tt",
        shared=["all"],
        editable_by="admin",
        customer="global",
    )

    clients.Password.edit("fooz", expect_ok=False).assert_status_code(404)
    clients.Password.edit("foo", title="foobu", comment="Something but nothing random")

    resp = clients.Password.get("foo")
    assert resp.json["extensions"] == {
        "comment": "Something but nothing random",
        "documentation_url": "",
        "owned_by": "admin",
        "editable_by": "admin",
        "shared": ["all"],
        "customer": "global",
    }


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls", "mock_password_file_regeneration")
def test_openapi_password_editable_by(clients: ClientRegistry) -> None:
    clients.ContactGroup.create("group1", "group1")

    clients.Password.create(
        ident="test",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by="group1",
        _owner="group1",
        expect_ok=False,
    ).assert_status_code(400)

    resp = clients.Password.create(
        ident="test_1",
        title="Checkmk",
        password="tt",
        shared=[],
        _owner="group1",
    )
    assert resp.json["extensions"]["editable_by"] == "group1"
    assert resp.json["extensions"]["owned_by"] == "group1"

    resp = clients.Password.create(
        ident="test_2",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by="group1",
    )
    assert resp.json["extensions"]["editable_by"] == "group1"
    assert resp.json["extensions"]["owned_by"] == "group1"

    resp = clients.Password.create(
        ident="test_3",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by=None,  # default should be admin
    )
    assert resp.json["extensions"]["editable_by"] == "admin"
    assert resp.json["extensions"]["owned_by"] == "admin"

    resp = clients.Password.edit("test_3", editable_by="group1")
    assert resp.json["extensions"]["editable_by"] == "group1"
    assert resp.json["extensions"]["owned_by"] == "group1"


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls", "mock_password_file_regeneration")
def test_openapi_password_customer(clients: ClientRegistry) -> None:
    resp = clients.Password.create(
        ident="test",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by="admin",
        customer="provider",
    )
    assert resp.json["extensions"]["customer"] == "provider"

    resp = clients.Password.edit("test", customer="global")
    assert resp.json["extensions"]["customer"] == "global"


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls", "mock_password_file_regeneration")
def test_openapi_password_delete(clients: ClientRegistry) -> None:
    clients.Password.create(
        ident="test",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by="admin",
        customer="provider",
    )
    resp = clients.Password.get_all()
    assert len(resp.json["value"]) == 1

    clients.Password.delete("invalid", expect_ok=False).assert_status_code(404)
    clients.Password.delete("test").assert_status_code(204)

    clients.Password.get("test", expect_ok=False).assert_status_code(404)
    resp = clients.Password.get_all()
    assert len(resp.json["value"]) == 0


@managedtest
@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_password_with_newlines(clients: ClientRegistry) -> None:
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

    clients.Password.create(
        ident="gcp",
        title="gcp",
        password=credentials_with_newlines,
        shared=[],
        editable_by="admin",
        customer="provider",
    )

    loaded = password_store.load(password_store.password_store_path())
    assert loaded["gcp"] == credentials_with_newlines.replace("\n", "")


@managedtest
@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_openapi_password_without_owner_regression(clients: ClientRegistry) -> None:
    clients.Password.create(
        ident="so_secret",
        title="so_secret",
        password="no_one_can_know",
        shared=["all"],
        editable_by="admin",
    )

    resp = clients.Password.get("so_secret")
    assert resp.json["extensions"].get("owned_by") is not None


@managedtest
def test_password_min_length_create(clients: ClientRegistry) -> None:
    resp = clients.Password.create(
        ident="so_secret",
        title="so_secret",
        password="",
        shared=["all"],
        editable_by="admin",
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert resp.json["fields"] == {"password": ["string '' is too short. The minimum length is 1."]}


@managedtest
@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_password_min_length_update(clients: ClientRegistry) -> None:
    clients.Password.create(
        ident="so_secret",
        title="so_secret",
        password="no_one_can_know",
        shared=["all"],
        editable_by="admin",
    )
    resp = clients.Password.edit(
        ident="so_secret",
        title="so_secret",
        editable_by="admin",
        password="",
        shared=["all"],
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert resp.json["fields"] == {"password": ["string '' is too short. The minimum length is 1."]}


@managedtest
def test_password_identifier_regex(clients: ClientRegistry) -> None:
    resp = clients.Password.create(
        ident="abcℕ",
        title="so_secret",
        password="no_one_can_know",
        shared=["all"],
        editable_by="admin",
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert resp.json["fields"] == {
        "ident": [
            "'abcℕ' does not match pattern. An identifier must only consist of letters, digits, dash and underscore and it must start with a letter or underscore."
        ]
    }
