#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any
from unittest import mock

import pytest
from pytest import MonkeyPatch

from tests.testlib.unit.rest_api_client import ClientRegistry

from cmk.ccc import version

from cmk.utils import paths

from cmk.gui.exceptions import MKUserError
from cmk.gui.openapi.endpoints.site_management.common import (
    default_config_example as _default_config,
)
from cmk.gui.openapi.endpoints.site_management.common import (
    no_replication_config_example as _no_replication_config,
)
from cmk.gui.rest_api_types.site_connection import (
    ConfigurationConnection,
    Connection,
    Proxy,
    SiteConfig,
    StatusHost,
)

DOMAIN_TYPE = "site_connection"


def _no_replication_config_with_site_id() -> tuple[SiteConfig, str]:
    config = _no_replication_config()
    return config, config["basic_settings"]["site_id"]


def _default_config_with_site_id() -> tuple[SiteConfig, str]:
    config = _default_config()
    return config, config["basic_settings"]["site_id"]


def test_get_a_site_connection(clients: ClientRegistry) -> None:
    site_id = "NO_SITE"
    resp = clients.SiteManagement.get(site_id=site_id)
    assert resp.json["domainType"] == DOMAIN_TYPE
    assert resp.json["id"] == site_id

    example_config = _no_replication_config()
    assert set(resp.json["extensions"].keys()) == set(example_config.keys())
    assert set(resp.json["extensions"]["basic_settings"].keys()) == set(
        example_config["basic_settings"].keys()
    )
    assert set(resp.json["extensions"]["status_connection"].keys()) == set(
        example_config["status_connection"].keys()
    )
    assert set(resp.json["extensions"]["configuration_connection"].keys()) == set(
        example_config["configuration_connection"].keys()
    )


def test_get_site_connection_that_doesnt_exist(clients: ClientRegistry) -> None:
    clients.SiteManagement.get(site_id="NON_SITE", expect_ok=False).assert_status_code(404)


def test_get_site_connections(clients: ClientRegistry) -> None:
    resp = clients.SiteManagement.get_all()
    assert resp.json["domainType"] == DOMAIN_TYPE
    assert resp.json["value"][0]["id"] == "NO_SITE"


def test_login(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.gui.fields.definitions.load_users", lambda: ["cmkadmin"])
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.do_site_login",
        lambda site_id, username, password, debug: "watosecret",
    )
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.trigger_remote_certs_creation",
        lambda site_id, settings, force, debug: None,
    )

    clients.SiteManagement.login(
        site_id="NO_SITE",
        username="cmkadmin",
        password="cmk",
    )


def test_login_site_doesnt_exist(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.gui.fields.definitions.load_users", lambda: ["cmkadmin"])
    clients.SiteManagement.login(
        site_id="NON_SITE",
        username="cmkadmin",
        password="cmk",
        expect_ok=False,
    ).assert_status_code(404)


def test_login_site_problem(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.gui.fields.definitions.load_users", lambda: ["cmkadmin"])

    class MockLoginException:
        def __init__(self, *args, **kwargs):
            raise Exception("There was a problem logging in.")

    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.do_site_login",
        MockLoginException,
    )
    clients.SiteManagement.login(
        site_id="NO_SITE",
        username="cmkadmin",
        password="cmk",
        expect_ok=False,
    ).assert_status_code(400)


def test_logout_site(clients: ClientRegistry) -> None:
    clients.SiteManagement.logout(site_id="NO_SITE")


def test_logout_site_that_doesnt_exist(clients: ClientRegistry) -> None:
    clients.SiteManagement.logout(
        site_id="NO_EXIST_SITE",
        expect_ok=False,
    ).assert_status_code(404)


def test_delete_site_connection(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    clients.SiteManagement.delete(site_id=site_id)


def test_delete_site_connection_problem(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    class MockDeleteException:
        def __init__(self, *args, **kwargs):
            raise MKUserError(varname=None, message="There was a problem deleting that site.")

    monkeypatch.setattr(
        "cmk.gui.watolib.sites.SiteManagement.delete_site",
        MockDeleteException,
    )
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    clients.SiteManagement.delete(
        site_id=site_id,
        expect_ok=False,
    ).assert_status_code(400)


def test_create_site_connection(clients: ClientRegistry) -> None:
    clients.SiteManagement.create(site_config=_default_config())


def test_create_site_connection_that_already_exists(
    clients: ClientRegistry,
) -> None:
    clients.SiteManagement.create(site_config=_default_config())
    clients.SiteManagement.create(
        site_config=_default_config(),
        expect_ok=False,
    ).assert_status_code(400)


keys_to_remove = ("basic_settings", "status_connection", "configuration_connection")


@pytest.mark.parametrize("key", keys_to_remove)
def test_create_site_connection_missing_config(
    clients: ClientRegistry,
    key: str,
) -> None:
    config = _default_config()
    config.pop(key)  # type: ignore[misc]
    clients.SiteManagement.create(
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


def test_create_then_get_site_connection(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    resp = clients.SiteManagement.get(site_id=site_id)
    assert resp.json["extensions"] == config


def test_create_site_connection_url_without_tld(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    url = "http://myhost:7323/myhost/check_mk/"

    config["configuration_connection"]["url_of_remote_site"] = url
    clients.SiteManagement.create(site_config=config)
    resp = clients.SiteManagement.get(site_id=site_id)
    assert resp.json["extensions"] == config


def test_update_site_connection(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


def test_update_site_connection_that_doesnt_exist(
    clients: ClientRegistry,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.update(
        site_id=site_id, site_config=config, expect_ok=False
    ).assert_status_code(404)


def test_update_site_connection_alias(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["basic_settings"]["alias"] = "edited alias"
    clients.SiteManagement.update(site_id=site_id, site_config=config)
    resp = clients.SiteManagement.get(site_id=site_id)
    assert resp.json["extensions"] == config


connection_test_data_200: list[Connection] = [
    {
        "socket_type": "tcp6",
        "host": "5402:1db8:95a3:0000:0000:9a2e:0480:8334",
        "port": 12345,
        "encrypted": False,
    },
    {
        "socket_type": "tcp6",
        "host": "5402:1db8:95a3:0000:0000:9a2e:0480:8334",
        "port": 12345,
        "encrypted": True,
        "verify": False,
    },
    {
        "socket_type": "tcp6",
        "host": "5402:1db8:95a3:0000:0000:9a2e:0480:8334",
        "port": 12345,
        "encrypted": True,
        "verify": True,
    },
    {"socket_type": "tcp", "host": "192.168.1.200", "port": 54321, "encrypted": False},
    {"socket_type": "unix", "path": "/abc/def/ghi"},
]


@pytest.mark.parametrize("data", connection_test_data_200)
def test_update_site_connection_status_connection_200(
    clients: ClientRegistry,
    data: Connection,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["status_connection"]["connection"] = data
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


connection_test_data_400: list[Connection] = [
    {
        "socket_type": "tcp6",
        "host": "192.167.23.2",
        "port": 12345,
        "encrypted": False,
        "verify": False,
    },
    {
        "socket_type": "tcp6",
        "host": "5402:1db8:95a3:0000:0000:9a2e:0480:8334",
        "port": 1234512345,
        "encrypted": False,
        "verify": False,
    },
    {"socket_type": "electrical_socket"},  # type: ignore[typeddict-item]
    {"socket_type": "unix"},
    {"socket_type": "tcp"},
    {"socket_type": "tcp6"},
    {"socket_type": "tcp6", "host": "5402:1db8:95a3:NOPE:9a2e:0480:8334"},
    {"socket_type": "tcp6", "host": "5402:1db8:95a3:0000:0000:9a2e:0480:8334", "port": 123456},
    {"host": "192.168.1.200", "port": 1234512345, "encrypted": False, "verify": False},
]


@pytest.mark.parametrize("data", connection_test_data_400)
def test_update_site_connection_status_connection_400(
    clients: ClientRegistry,
    data: Connection,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["status_connection"]["connection"] = data
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


proxy_test_data_200: list[Proxy] = [
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {
            "channels": 9,
            "heartbeat": {"interval": 4, "timeout": 7.2},
            "channel_timeout": 10.0,
            "query_timeout": 232.5,
            "connect_retry": 5.1,
            "cache": False,
        },
        "tcp": {"port": 6565, "only_from": ["192.168.1.1", "192.168.1.2"], "tls": True},
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {
            "channels": 5,
        },
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {
            "channels": 9,
            "heartbeat": {"interval": 9, "timeout": 3.4},
        },
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {
            "channels": 9,
            "heartbeat": {"interval": 4, "timeout": 7.2},
            "channel_timeout": 10.0,
        },
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {
            "channels": 9,
            "heartbeat": {"interval": 4, "timeout": 7.2},
            "channel_timeout": 10.0,
            "query_timeout": 343.5,
        },
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {
            "channels": 9,
            "heartbeat": {"interval": 4, "timeout": 7.2},
            "channel_timeout": 10.0,
            "query_timeout": 232.5,
            "connect_retry": 6.53,
        },
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {
            "channels": 9,
            "heartbeat": {"interval": 4, "timeout": 7.2},
            "channel_timeout": 10.0,
            "query_timeout": 232.5,
            "connect_retry": 5.1,
            "cache": True,
        },
    },
    {
        "use_livestatus_daemon": "direct",
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": True,
        "tcp": {"port": 6565, "only_from": ["192.168.1.1", "192.168.1.2"], "tls": False},
    },
]

proxy_test_data_400: list[Proxy] = [
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {
            "connect_retry": -5.1,
        },
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": False,
        "params": {"invalid_param": True},  # type: ignore[typeddict-unknown-key]
    },
    {
        "use_livestatus_daemon": "direct",
        "global_settings": False,
        "params": {"channels": 9},
    },
    {
        "use_livestatus_daemon": "direct",
        "global_settings": False,
        "tcp": {"port": 6565, "only_from": ["192.168.1.1", "192.168.1.2"], "tls": True},
    },
    {
        "use_livestatus_daemon": "direct",
        "global_settings": False,
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": True,
        "tcp": {"only_from": ["192.168.1.1", "192.168.1.2"], "tls": True},
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": True,
        "tcp": {"port": 8698790007},
    },
    {
        "use_livestatus_daemon": "with_proxy",
        "global_settings": True,
        "tcp": {"port": 44232, "only_from": ["192.168.1.abc", "192.168.1.2"]},
    },
]


@pytest.mark.parametrize("data", proxy_test_data_200)
def test_update_site_connection_proxy_200(
    clients: ClientRegistry,
    data: Proxy,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["status_connection"]["proxy"] = data
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


@pytest.mark.parametrize("data", proxy_test_data_400)
def test_update_site_connection_proxy_400(
    clients: ClientRegistry,
    data: Proxy,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["status_connection"]["proxy"] = data
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


def test_update_site_connection_user_sync(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    edited_user_sync = {"sync_with_ldap_connections": "disabled"}
    config["configuration_connection"]["user_sync"] = edited_user_sync
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


def test_update_site_connection_user_sync_with_ldap_connections_200(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    connection_choices = [
        ("LDAP_1", "LDAP_1 (ldap)"),
        ("LDAP_2", "LDAP_2 (ldap)"),
        ("LDAP_3", "LDAP_3 (ldap)"),
    ]
    monkeypatch.setattr(
        "cmk.gui.fields.custom_fields.connection_choices", lambda: connection_choices
    )
    monkeypatch.setattr("cmk.gui.watolib.sites.connection_choices", lambda: connection_choices)

    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    edited_user_sync = {
        "sync_with_ldap_connections": "ldap",
        "ldap_connections": ["LDAP_1", "LDAP_2", "LDAP_3"],
    }
    config["configuration_connection"]["user_sync"] = edited_user_sync
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


def test_update_site_connection_user_sync_with_ldap_connections_400(
    clients: ClientRegistry,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    edited_user_sync = {
        "sync_with_ldap_connections": "ldap",
        "ldap_connections": ["LDAP_1", "LDAP_2", "LDAP_3"],
    }
    config["configuration_connection"]["user_sync"] = edited_user_sync
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


config_cnx_test_data_200: list[ConfigurationConnection] = [
    {
        "enable_replication": True,
        "url_of_remote_site": "http://localhost/heute_remote_site_id_1/check_mk/",
        "disable_remote_configuration": True,
        "ignore_tls_errors": True,
        "direct_login_to_web_gui_allowed": True,
        "user_sync": {
            "sync_with_ldap_connections": "all",
        },
        "replicate_event_console": True,
        "replicate_extensions": True,
        "message_broker_port": 5672,
    },
    {
        "enable_replication": False,
    },
    {
        "enable_replication": True,
        "url_of_remote_site": "http://localhost/heute_remote_site_id_1/check_mk/",
        "disable_remote_configuration": True,
        "ignore_tls_errors": True,
        "direct_login_to_web_gui_allowed": True,
        "user_sync": {
            "sync_with_ldap_connections": "disabled",
        },
        "replicate_event_console": True,
        "replicate_extensions": True,
        "message_broker_port": 5672,
    },
]


@pytest.mark.parametrize("data", config_cnx_test_data_200)
def test_update_configuration_connection_200(
    clients: ClientRegistry,
    data: ConfigurationConnection,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["configuration_connection"] = data
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


config_cnx_test_data_400: list[ConfigurationConnection] = [
    {
        "user_sync": {
            "sync_with_ldap_connections": "all",
        },
    },
    {
        "user_sync": {
            "sync_with_ldap_connections": "INVALID-OPTION",
        },
    },
    {
        "enable_replication": False,
        "url_of_remote_site": "http://localhost/heute_remote_site_id_1/check_mk/",
        "disable_remote_configuration": False,
        "ignore_tls_errors": False,
        "direct_login_to_web_gui_allowed": False,
        "user_sync": {
            "sync_with_ldap_connections": "all",
        },
        "replicate_event_console": False,
        "replicate_extensions": False,
        "invalid_attribute": True,  # type: ignore[typeddict-unknown-key]
    },
    {
        "enable_replication": True,
        "disable_remote_configuration": True,
        "ignore_tls_errors": True,
        "direct_login_to_web_gui_allowed": True,
        "user_sync": {
            "sync_with_ldap_connections": "all",
        },
        "replicate_event_console": True,
        "replicate_extensions": True,
    },
]


@pytest.mark.parametrize("data", config_cnx_test_data_400)
def test_update_configuration_connection_400(
    clients: ClientRegistry,
    data: ConfigurationConnection,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["configuration_connection"] = data
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


def test_update_status_host_200(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    class MockHost:
        @classmethod
        def host(cls, *args: Any) -> Any:
            mock_host = mock.Mock()
            mock_host.may = mock.Mock(return_value=True)
            return mock_host

    monkeypatch.setattr("cmk.gui.fields.definitions.Host", MockHost)

    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    data: StatusHost = {"status_host_set": "enabled", "site": "NO_SITE", "host": "host1"}
    config["status_connection"]["status_host"] = data
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


status_host_test_data: list[StatusHost] = [
    {"status_host_set": "disabled", "site": "NO_SITE", "host": "host1"},
    {"status_host_set": "enabled", "site": "NO_SITE"},
    {"status_host_set": "enabled", "host": "host1"},
]


@pytest.mark.parametrize("data", status_host_test_data)
def test_update_status_host_400(
    clients: ClientRegistry,
    data: StatusHost,
    monkeypatch: MonkeyPatch,
) -> None:
    class MockHost:
        @classmethod
        def host(cls, *args: Any) -> Any:
            mock_host = mock.Mock()
            mock_host.may = mock.Mock(return_value=True)
            return mock_host

    monkeypatch.setattr("cmk.gui.fields.definitions.Host", MockHost)

    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["status_connection"]["status_host"] = data
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


url_of_remote_site_test_data_200: list[str] = [
    "http://localhost/abc/check_mk/",
    "https://localhost/abc/check_mk/",
]


@pytest.mark.parametrize("data", url_of_remote_site_test_data_200)
def test_update_url_of_remote_site_200(
    clients: ClientRegistry,
    data: str,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["configuration_connection"]["url_of_remote_site"] = data
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


url_of_remote_site_test_data_400: list[str] = [
    "http://localhost/abc/123",
    "https://localhost/abc/123",
    "http//localhost/abc/123",
    "https:localhost/abc/123",
    "httpss://localhost/abc/123",
    "htttp://localhost/abc/123",
]


@pytest.mark.parametrize("data", url_of_remote_site_test_data_400)
def test_update_url_of_remote_site_400(
    clients: ClientRegistry,
    data: str,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["configuration_connection"]["url_of_remote_site"] = data
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


def test_update_url_prefix_200(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["status_connection"]["url_prefix"] = "/remote_site_1/"
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    assert resp.json["extensions"] == config


def test_update_url_prefix_400(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["status_connection"]["url_prefix"] = "/remote_site_1"
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


def test_post_site_config_customer_field(clients: ClientRegistry) -> None:
    config = _default_config()
    if version.edition(paths.omd_root) is version.Edition.CME:
        r = clients.SiteManagement.create(site_config=config)
        assert "customer" in r.json["extensions"]["basic_settings"]
        del config["basic_settings"]["customer"]
        clients.SiteManagement.create(site_config=config, expect_ok=False).assert_status_code(400)
    else:
        r = clients.SiteManagement.create(site_config=config)
        assert "customer" not in r.json["extensions"]["basic_settings"]
        config["basic_settings"].update({"customer": "provider"})
        clients.SiteManagement.create(site_config=config, expect_ok=False).assert_status_code(400)


def test_validation_layer_min_config(clients: ClientRegistry) -> None:
    r: SiteConfig = {
        "basic_settings": {
            "site_id": "required_site_id",
            "alias": "required_site_alias",
        },
        "status_connection": {
            "connection": {
                "socket_type": "unix",
                "path": "/path/to/socket",
            },
            "connect_timeout": 5,
            "proxy": {"use_livestatus_daemon": "direct"},
            "status_host": {"status_host_set": "disabled"},
        },
        "configuration_connection": {
            "enable_replication": True,
            "url_of_remote_site": "http://localhost/heute_remote_site_id_1/check_mk/",
            "disable_remote_configuration": True,
            "ignore_tls_errors": False,
            "direct_login_to_web_gui_allowed": True,
            "user_sync": {"sync_with_ldap_connections": "all"},
            "replicate_event_console": True,
            "replicate_extensions": True,
            "message_broker_port": 5672,
        },
    }
    if version.edition(paths.omd_root) is version.Edition.CME:
        r["basic_settings"]["customer"] = "provider"

    clients.SiteManagement.create(site_config=r)


def test_create_no_sync_site_connection(clients: ClientRegistry) -> None:
    config, site_id = _no_replication_config_with_site_id()
    config["configuration_connection"] = {"enable_replication": False}
    clients.SiteManagement.create(site_config=config)

    resp = clients.SiteManagement.get(site_id=site_id)
    assert resp.json["extensions"]["configuration_connection"] == config["configuration_connection"]
