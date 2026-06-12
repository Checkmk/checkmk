#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

from cmk.gui.config import active_config
from cmk.gui.ldap_integration.ldap_connector import LDAPUserConnector
from cmk.gui.user_connection_config_types import (
    Fixed,
    LDAPConnectionConfigFixed,
    LDAPUserConnectionConfig,
)
from cmk.gui.userdb import UserConnectionConfigFile
from tests.testlib.rest_api_client import ClientRegistry


# Mocking wato_audit.log as its contents are not used in these tests and accessing it causes flaky results.
@pytest.fixture(autouse=True)
def mock_log_audit_file(mocker: MockerFixture) -> Iterator[None]:
    mocker.patch("cmk.gui.watolib.audit_log.log_audit")
    yield


def _create_ldap_connection(ldap_id: str) -> None:
    ldap_config = LDAPUserConnectionConfig(
        id=ldap_id,
        description="",
        comment="",
        docu_url="",
        disabled=False,
        directory_type=(
            "ad",
            LDAPConnectionConfigFixed(connect_to=("fixed_list", Fixed(server="10.200.3.32"))),
        ),
        user_dn="ou=users,dc=corp,dc=de",
        user_scope="sub",
        user_id_umlauts="keep",
        group_dn="",
        group_scope="sub",
        active_plugins={},
        cache_livetime=300,
        type="ldap",
    )
    UserConnectionConfigFile().save([ldap_config], pprint_value=False)
    active_config.user_connections = [ldap_config]


def test_test_non_existing_connection(clients: ClientRegistry) -> None:
    resp = clients.LdapConnection.test_connection("non_existing", expect_ok=False)
    assert resp.status_code == 404


def test_test_connection_returns_structured_results(
    clients: ClientRegistry, mocker: MockerFixture
) -> None:
    _create_ldap_connection("LDAP_1")

    def _passing_test(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
        return True, "All fine"

    def _failing_test(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
        return False, "Something is wrong"

    mocker.patch(
        "cmk.gui.ldap_integration.api.test_connection.diagnostic_tests",
        return_value=[("Connection", _passing_test), ("User Base-DN", _failing_test)],
    )

    resp = clients.LdapConnection.test_connection("LDAP_1")
    assert resp.json == {
        "connection_id": "LDAP_1",
        "success": False,
        "servers": [
            {
                "server": "10.200.3.32",
                "results": [
                    {"title": "Connection", "success": True, "details": "All fine"},
                    {"title": "User Base-DN", "success": False, "details": "Something is wrong"},
                ],
            }
        ],
    }


def test_test_connection_handles_test_exceptions(
    clients: ClientRegistry, mocker: MockerFixture
) -> None:
    _create_ldap_connection("LDAP_1")

    def _raising_test(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
        raise RuntimeError("boom")

    mocker.patch(
        "cmk.gui.ldap_integration.api.test_connection.diagnostic_tests",
        return_value=[("Connection", _raising_test)],
    )

    resp = clients.LdapConnection.test_connection("LDAP_1")
    assert resp.json["success"] is False
    assert resp.json["servers"][0]["results"] == [
        {"title": "Connection", "success": False, "details": "Exception: boom"}
    ]
