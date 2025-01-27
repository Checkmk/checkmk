#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from pytest import MonkeyPatch

from tests.testlib.unit.rest_api_client import (
    ClientRegistry,
)

from cmk.gui.watolib.broker_connections import BrokerConnectionInfo, SiteConnectionInfo

TEST_CONNECTION_ID = "connection_1"
TEST_CONNECTION_CONFIG = BrokerConnectionInfo(
    connecter=SiteConnectionInfo(site_id="remote_1"),
    connectee=SiteConnectionInfo(site_id="remote_2"),
)


@pytest.fixture(name="create_test_broker_connection", scope="function")
def _create_broker_connection(monkeypatch: MonkeyPatch, clients: ClientRegistry) -> None:
    # fake existent sites ids
    monkeypatch.setattr(
        "cmk.gui.fields.definitions.SiteField._validate",
        lambda x, y: None,
    )
    clients.BrokerConnection.create(
        {
            "connection_id": TEST_CONNECTION_ID,
            "connection_config": TEST_CONNECTION_CONFIG,
        }
    )


def test_openapi_get_empty_broker_connections(clients: ClientRegistry) -> None:
    res = clients.BrokerConnection.get_all()
    res.assert_status_code(200)
    assert res.json["value"] == []


def test_openapi_get_broker_connections(
    clients: ClientRegistry, create_test_broker_connection: None
) -> None:
    res = clients.BrokerConnection.get_all()
    res.assert_status_code(200)
    assert res.json["value"][0]["id"] == TEST_CONNECTION_ID
    assert res.json["value"][0]["extensions"] == TEST_CONNECTION_CONFIG


def test_openapi_get_broker_connection(
    clients: ClientRegistry, create_test_broker_connection: None
) -> None:
    res = clients.BrokerConnection.get(TEST_CONNECTION_ID)
    res.assert_status_code(200)
    assert res.json["id"] == TEST_CONNECTION_ID
    assert res.json["extensions"] == TEST_CONNECTION_CONFIG


def test_openapi_get_non_existent_broker_connection(
    clients: ClientRegistry, create_test_broker_connection: None
) -> None:
    res = clients.BrokerConnection.get("non existent id", expect_ok=False)
    res.assert_status_code(404)


@pytest.mark.parametrize(
    "connection_id, connection_config",
    [
        (
            "conn1",
            BrokerConnectionInfo(
                connecter=SiteConnectionInfo(site_id="heute_remote_1"),
                connectee=SiteConnectionInfo(site_id="heute_remote_2"),
            ),
        ),
        (
            "conn2",
            BrokerConnectionInfo(
                connecter=SiteConnectionInfo(site_id="heute_remote_2"),
                connectee=SiteConnectionInfo(site_id="heute_remote_3"),
            ),
        ),
    ],
)
def test_openapi_create_broker_connection(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
    connection_id: str,
    connection_config: BrokerConnectionInfo,
) -> None:
    # fake existent sites ids
    monkeypatch.setattr(
        "cmk.gui.fields.definitions.SiteField._validate",
        lambda x, y: None,
    )

    res = clients.BrokerConnection.create(
        {
            "connection_id": connection_id,
            "connection_config": connection_config,
        }
    )
    res.assert_status_code(200)
    assert res.json["id"] == connection_id
    assert res.json["extensions"] == connection_config


def test_openapi_create_existent_broker_connection(
    clients: ClientRegistry, create_test_broker_connection: None
) -> None:
    res = clients.BrokerConnection.create(
        {
            "connection_id": TEST_CONNECTION_ID,
            "connection_config": TEST_CONNECTION_CONFIG,
        },
        expect_ok=False,
    )
    res.assert_status_code(400)


def test_openapi_create_broker_connection_invalid_connection_id(
    clients: ClientRegistry, create_test_broker_connection: None
) -> None:
    res = clients.BrokerConnection.create(
        {
            "connection_id": "not acceptable id:",
            "connection_config": TEST_CONNECTION_CONFIG,
        },
        expect_ok=False,
    )
    res.assert_status_code(400)


def test_openapi_create_broker_connection_sites_already_connected(
    clients: ClientRegistry, create_test_broker_connection: None
) -> None:
    res = clients.BrokerConnection.create(
        {
            "connection_id": "new_id",
            "connection_config": TEST_CONNECTION_CONFIG,
        },
        expect_ok=False,
    )
    res.assert_status_code(400)


def test_openapi_create_broker_connection_same_sites(
    clients: ClientRegistry, create_test_broker_connection: None
) -> None:
    res = clients.BrokerConnection.create(
        {
            "connection_id": "new_id",
            "connection_config": BrokerConnectionInfo(
                connecter=SiteConnectionInfo(site_id="heute_remote_2"),
                connectee=SiteConnectionInfo(site_id="heute_remote_2"),
            ),
        },
        expect_ok=False,
    )
    res.assert_status_code(400)


def test_openapi_update_broker_connection(
    clients: ClientRegistry,
    create_test_broker_connection: None,
) -> None:
    new_connection_config = BrokerConnectionInfo(
        connecter=SiteConnectionInfo(site_id="remote_3"),
        connectee=SiteConnectionInfo(site_id="remote_4"),
    )

    res = clients.BrokerConnection.edit(
        connection_id=TEST_CONNECTION_ID,
        payload={"connection_config": new_connection_config},
        etag="valid_etag",
    )
    res.assert_status_code(200)
    assert res.json["id"] == TEST_CONNECTION_ID
    assert res.json["extensions"] == new_connection_config


def test_openapi_update_missing_broker_connection(
    clients: ClientRegistry,
    create_test_broker_connection: None,
) -> None:
    res = clients.BrokerConnection.edit(
        connection_id="Non_existent_id",
        payload={"connection_config": TEST_CONNECTION_CONFIG},
        expect_ok=False,
    )
    res.assert_status_code(404)


def test_openapi_update_broker_connection_same_site_ids(
    clients: ClientRegistry,
    create_test_broker_connection: None,
) -> None:
    clients.BrokerConnection.create(
        {
            "connection_id": "connection_2",
            "connection_config": BrokerConnectionInfo(
                connecter=SiteConnectionInfo(site_id="remote_3"),
                connectee=SiteConnectionInfo(site_id="remote_4"),
            ),
        }
    )

    new_connection_config = BrokerConnectionInfo(
        connecter=SiteConnectionInfo(site_id="remote_4"),
        connectee=SiteConnectionInfo(site_id="remote_3"),
    )

    res = clients.BrokerConnection.edit(
        connection_id=TEST_CONNECTION_ID,
        payload={"connection_config": new_connection_config},
        expect_ok=False,
        etag="valid_etag",
    )
    res.assert_status_code(400)


def test_openapi_delete_broker_connection(
    clients: ClientRegistry,
    create_test_broker_connection: None,
) -> None:
    res = clients.BrokerConnection.delete(connection_id=TEST_CONNECTION_ID, etag="valid_etag")
    res.assert_status_code(204)


def test_openapi_delete_non_existent_broker_connection(
    clients: ClientRegistry,
) -> None:
    res = clients.BrokerConnection.delete(
        connection_id=TEST_CONNECTION_ID,
        expect_ok=False,
    )
    res.assert_status_code(404)
