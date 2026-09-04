#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from cmk.ccc import version
from cmk.ccc.site import SiteId
from cmk.gui.exceptions import MKUserError
from cmk.gui.openapi.api_endpoints.site_management.models.config_example import (
    default_config_example as _default_config,
)
from cmk.gui.rest_api_types.site_connection import (
    ConfigurationConnection,
    Connection,
    Proxy,
    SiteConfig,
    StatusHost,
)
from cmk.gui.watolib.site_changes import SiteChanges
from cmk.gui.watolib.sites import SitesConfigFile
from cmk.livestatus_client import SAMLAuthenticationEntry, SiteConfiguration
from cmk.utils import paths
from tests.testlib.rest_api_client import ClientRegistry

DOMAIN_TYPE = "site_connection"


def _default_config_with_site_id() -> tuple[SiteConfig, str]:
    config = _default_config()
    return config, config["basic_settings"]["site_id"]


def test_get_a_site_connection(clients: ClientRegistry) -> None:
    site_id = "NO_SITE"
    resp = clients.SiteManagement.get(site_id=site_id)
    assert resp.json["domainType"] == DOMAIN_TYPE
    assert resp.json["id"] == site_id

    example_config = _default_config()
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


def test_login_replication_enabled(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    config, remote_site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    monkeypatch.setattr("cmk.gui.fields.definitions.load_users", lambda: ["cmkadmin"])
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.do_site_login",
        lambda site_id, username, password, debug: "watosecret",
    )
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.trigger_remote_certs_creation",
        lambda site_id, settings, force, debug: None,
    )
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.distribute_license_to_remotes",
        lambda logger, remote_automation_configs: None,
    )

    clients.SiteManagement.login(
        site_id=remote_site_id,
        username="cmkadmin",
        password="cmk",
    )


def test_login_double_call_no_effect(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    config, remote_site_id = _default_config_with_site_id()
    site_login_mock = MagicMock()
    site_login_mock.return_value = "watosecret"
    trigger_remote_certs_mock = MagicMock()
    distribute_license_mock = MagicMock()
    clients.SiteManagement.create(site_config=config)
    monkeypatch.setattr("cmk.gui.fields.definitions.load_users", lambda: ["cmkadmin"])
    monkeypatch.setattr("cmk.gui.watolib.site_management.do_site_login", site_login_mock)
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.trigger_remote_certs_creation", trigger_remote_certs_mock
    )
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.distribute_license_to_remotes", distribute_license_mock
    )

    clients.SiteManagement.login(
        site_id=remote_site_id,
        username="cmkadmin",
        password="cmk",
    )
    clients.SiteManagement.login(
        site_id=remote_site_id,
        username="cmkadmin",
        password="cmk",
    )

    site_login_mock.assert_called_once()
    trigger_remote_certs_mock.assert_called_once()
    distribute_license_mock.assert_called_once()


def test_login_replication_disabled(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    config, remote_site_id = _default_config_with_site_id()
    config["configuration_connection"]["enable_replication"] = False
    clients.SiteManagement.create(site_config=config)
    monkeypatch.setattr("cmk.gui.fields.definitions.load_users", lambda: ["cmkadmin"])
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.do_site_login",
        lambda site_id, username, password, debug: "watosecret",
    )
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.trigger_remote_certs_creation",
        lambda site_id, settings, force, debug: None,
    )
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.distribute_license_to_remotes",
        lambda logger, remote_automation_configs: None,
    )

    # TODO fix this.  We shouldn't return a 500 on login failure
    clients.SiteManagement.login(
        site_id=remote_site_id, username="cmkadmin", password="cmk", expect_ok=False
    ).assert_status_code(500)


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


def test_create_site_connection_records_pending_change_for_new_site(
    clients: ClientRegistry,
) -> None:
    config, new_site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)

    recorded = [entry["action_name"] for entry in SiteChanges(SiteId(new_site_id)).read()]
    assert "edit-sites" in recorded, (
        f"Expected an 'edit-sites' pending change for the newly created site "
        f"{new_site_id!r}, but only found: {recorded}"
    )


@pytest.mark.parametrize(
    "site_id",
    [
        pytest.param("site-1", id="dash"),
        pytest.param("1site", id="leading_digit"),
        pytest.param("a" * 17, id="too_long"),
        pytest.param("remote\n", id="trailing_newline"),
    ],
)
def test_create_site_connection_with_invalid_site_id(
    clients: ClientRegistry,
    site_id: str,
) -> None:
    config = _default_config()
    config["basic_settings"]["site_id"] = site_id
    clients.SiteManagement.create(
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


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
    # NOTE: The whole test is very questionable from a typing perspecitve: Even if we make the type
    # of `key` stricter via a `Literal`, things are incorrect: The key/value pairs we remove are
    # required, so the whole typing is a lie here.
    config.pop(key)  # type: ignore[misc]
    clients.SiteManagement.create(
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


def test_create_then_get_site_connection(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    resp = clients.SiteManagement.get(site_id=site_id)
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


def test_create_site_connection_url_without_tld(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    url = "http://myhost:7323/myhost/check_mk/"

    config["configuration_connection"]["url_of_remote_site"] = url
    clients.SiteManagement.create(site_config=config)
    resp = clients.SiteManagement.get(site_id=site_id)
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


def test_update_site_connection(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


def test_update_site_connection_ignores_site_id_from_body(clients: ClientRegistry) -> None:
    """The site ID from the path wins, the one in the request body is ignored."""
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)

    config["basic_settings"]["site_id"] = "NO_SITE"
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)

    assert resp.json["id"] == site_id
    assert resp.json["extensions"]["basic_settings"]["site_id"] == site_id
    stored = clients.SiteManagement.get(site_id=site_id)
    assert stored.json["extensions"]["basic_settings"]["site_id"] == site_id


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
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


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
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


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
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


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
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


def test_update_site_connection_preserves_settings_it_cannot_express(
    clients: ClientRegistry,
) -> None:
    """Any stored key the rest-api does not model must survive an update.

    The unmodeled keys are derived from the `SiteConfiguration` TypedDict rather than
    hard-coded, so a key added there is covered automatically -- hard-coding is how the
    `authentication_connections` and `globals` regressions slipped in unnoticed.
    """

    def _stored_config(site_id: str) -> SiteConfiguration:
        """The site connection as it actually is on disk, bypassing the rest-api."""
        return SitesConfigFile().load_for_reading()[SiteId(site_id)]

    # `cache` and `tls` are computed at runtime when building a livestatus connection and never
    # written to sites.mk. `customer` is only modeled by the rest-api in the editions that have it
    # (see tests/openapi/nonfree/ultimatemt/test_openapi_site_management_customer.py), not in the
    # community edition this test runs under.
    not_applicable_keys = {"cache", "tls", "customer"}
    all_known_keys = set(SiteConfiguration.__annotations__) - not_applicable_keys

    # create the config via the rest-api:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)

    rest_api_keys = set(_stored_config(site_id))
    unmodeled_keys = all_known_keys - rest_api_keys
    assert unmodeled_keys, (
        "the rest-api now models every known site connection key -- "
        "this test (and the carve-outs in edit_site_connection_v1) can be simplified"
    )

    # simulate settings that only Setup (or a direct login, for `secret`) can produce, one sentinel
    # value per key the rest-api does not know about:
    sentinel_values = {key: f"__sentinel_{key}__" for key in unmodeled_keys}
    sites_config_file = SitesConfigFile()
    sites = sites_config_file.load_for_modification()
    sites[SiteId(site_id)].update(sentinel_values)  # type: ignore[typeddict-item]
    sites_config_file.save(sites, pprint_value=False)

    # update using the rest-api:
    clients.SiteManagement.update(site_id=site_id, site_config=config)

    stored_after_update = _stored_config(site_id)
    for key, value in sentinel_values.items():
        assert stored_after_update.get(key) == value, (
            f"{key!r} was dropped by a rest-api update -- carry it over in "
            "edit_site_connection_v1, the same way `secret` already is"
        )


def test_update_site_connection_authentication_connections(clients: ClientRegistry) -> None:
    clients.LdapConnection.create(
        ldap_data={
            "general_properties": {"id": "LDAP_1"},
            "ldap_connection": {
                "directory_type": {
                    "type": "active_directory_manual",
                    "ldap_server": "10.200.3.32",
                },
            },
        }
    )
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["configuration_connection"]["authentication_connections"] = {
        "type": "list",
        "connections": [{"type": "ldap", "connection_id": "LDAP_1"}],
    }
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config

    stored = SitesConfigFile().load_for_reading()[SiteId(site_id)]
    assert stored["authentication_connections"] == [("ldap", "LDAP_1")]


@pytest.mark.parametrize(
    "authentication_connections",
    [
        {"type": "all", "connection_types": []},
        {"type": "list", "connections": []},
    ],
)
def test_update_site_connection_empty_authentication_connections_400(
    clients: ClientRegistry,
    authentication_connections: dict[str, object],
) -> None:
    # reflecting gui behavior in the REST-API
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["configuration_connection"]["authentication_connections"] = authentication_connections
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


@pytest.fixture(name="saml_connection")
def _saml_connection(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.converter.get_saml_connections",
        lambda: {"saml_1": {}},
    )


def test_site_connection_saml_authentication_connection_round_trip(
    clients: ClientRegistry,
    saml_connection: None,
) -> None:
    config, site_id = _default_config_with_site_id()
    remote_site_url = config["configuration_connection"]["url_of_remote_site"]
    clients.SiteManagement.create(site_config=config)

    # SAML connections can only be configured in Setup, in editions supporting them:
    sites_config_file = SitesConfigFile()
    sites = sites_config_file.load_for_modification()
    sites[SiteId(site_id)]["authentication_connections"] = [
        (
            "saml",
            SAMLAuthenticationEntry(
                connection_id="saml_1",
                metadata_endpoint="http://localhost/site/check_mk/saml_metadata.py",
                acs_endpoint="http://localhost/site/check_mk/saml_acs.py",
            ),
        )
    ]
    sites_config_file.save(sites, pprint_value=False)

    # the endpoint URLs are derived, so the rest-api does not return them ...
    resp = clients.SiteManagement.get(site_id=site_id)
    config = resp.json["extensions"]
    assert config["configuration_connection"]["authentication_connections"] == {
        "type": "list",
        "connections": [{"type": "saml", "connection_id": "saml_1"}],
    }

    # ... but does store them, just like the site editor:
    config.pop("logged_in", None)
    clients.SiteManagement.update(site_id=site_id, site_config=config)
    stored = SitesConfigFile().load_for_reading()[SiteId(site_id)]
    assert stored["authentication_connections"] == [
        (
            "saml",
            {
                "connection_id": "saml_1",
                "metadata_endpoint": f"{remote_site_url}saml_metadata.py?RelayState=saml_1",
                "acs_endpoint": f"{remote_site_url}saml_acs.py?acs",
            },
        )
    ]


def test_update_site_connection_unknown_saml_authentication_connection_400(
    clients: ClientRegistry,
    saml_connection: None,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["configuration_connection"]["authentication_connections"] = {
        "type": "list",
        "connections": [{"type": "saml", "connection_id": "saml_unknown"}],
    }
    clients.SiteManagement.update(
        site_id=site_id,
        site_config=config,
        expect_ok=False,
    ).assert_status_code(400)


def test_update_site_connection_saml_authentication_connection_needs_global_permission_403(
    clients: ClientRegistry,
    saml_connection: None,
) -> None:
    """Holding "wato.sites" alone must not reveal which SAML connections exist."""
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)

    clients.UserRole.clone(body={"role_id": "admin", "new_role_id": "site_admin"})
    clients.UserRole.edit(role_id="site_admin", body={"new_permissions": {"wato.global": "no"}})
    clients.User.create(
        username="site_admin",
        fullname="site_admin",
        roles=["site_admin"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )
    clients.SiteManagement.set_credentials("site_admin", "supersecretish")

    details = []
    for saml_id in ("saml_1", "saml_unknown"):
        config["configuration_connection"]["authentication_connections"] = {
            "type": "list",
            "connections": [{"type": "saml", "connection_id": saml_id}],
        }
        resp = clients.SiteManagement.update(site_id=site_id, site_config=config, expect_ok=False)
        resp.assert_status_code(403)
        details.append(resp.json["detail"])
    assert details[0] == details[1]


def test_update_site_connection_user_sync_with_ldap_connections_200(
    clients: ClientRegistry,
) -> None:
    connection_choices = [
        ("LDAP_1", "LDAP_1 (ldap)"),
        ("LDAP_2", "LDAP_2 (ldap)"),
        ("LDAP_3", "LDAP_3 (ldap)"),
    ]
    for ldap_id, _alias in connection_choices:
        clients.LdapConnection.create(
            ldap_data={
                "general_properties": {"id": ldap_id},
                "ldap_connection": {
                    "directory_type": {
                        "type": "active_directory_manual",
                        "ldap_server": "10.200.3.32",
                    },
                },
            }
        )

    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    edited_user_sync = {
        "sync_with_ldap_connections": "ldap",
        "ldap_connections": ["LDAP_1", "LDAP_2", "LDAP_3"],
    }
    config["configuration_connection"]["user_sync"] = edited_user_sync
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


def test_update_site_connection_user_sync_no_permission_does_not_leak_ldap_existence(
    clients: ClientRegistry,
) -> None:
    clients.LdapConnection.create(
        ldap_data={
            "general_properties": {"id": "LDAP_1"},
            "ldap_connection": {
                "directory_type": {
                    "type": "active_directory_manual",
                    "ldap_server": "10.200.3.32",
                },
            },
        }
    )
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)

    clients.User.create(
        username="unprivileged",
        fullname="unprivileged",
        roles=["user"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )
    clients.SiteManagement.set_credentials("unprivileged", "supersecretish")

    details = []
    for ldap_id in ("LDAP_1", "LDAP_unknown"):
        config["configuration_connection"]["user_sync"] = {
            "sync_with_ldap_connections": "ldap",
            "ldap_connections": [ldap_id],
        }
        resp = clients.SiteManagement.update(site_id=site_id, site_config=config, expect_ok=False)
        resp.assert_status_code(403)
        details.append(resp.json["detail"])
    assert details[0] == details[1]


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
        "authentication_connections": {
            "type": "all",
            "connection_types": ["ldap", "saml"],
        },
        "user_sync": {
            "sync_with_ldap_connections": "all",
        },
        "replicate_event_console": True,
        "replicate_extensions": True,
        "message_broker_port": 5672,
        "is_trusted": False,
    },
    {
        "enable_replication": False,
        "url_of_remote_site": "",
        "disable_remote_configuration": True,
        "ignore_tls_errors": True,
        "direct_login_to_web_gui_allowed": True,
        "authentication_connections": {
            "type": "all",
            "connection_types": ["ldap", "saml"],
        },
        "user_sync": {
            "sync_with_ldap_connections": "all",
        },
        "replicate_event_console": True,
        "replicate_extensions": True,
        "message_broker_port": 5672,
        "is_trusted": False,
    },
    {
        "enable_replication": True,
        "url_of_remote_site": "http://localhost/heute_remote_site_id_1/check_mk/",
        "disable_remote_configuration": True,
        "ignore_tls_errors": True,
        "direct_login_to_web_gui_allowed": True,
        "authentication_connections": {"type": "disabled"},
        "user_sync": {
            "sync_with_ldap_connections": "disabled",
        },
        "replicate_event_console": True,
        "replicate_extensions": True,
        "message_broker_port": 5672,
        "is_trusted": False,
    },
]


@pytest.mark.parametrize("data", config_cnx_test_data_200)
def test_update_configuration_connection_200(  # type: ignore[misc]
    clients: ClientRegistry,
    data: ConfigurationConnection,
) -> None:
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    config["configuration_connection"] = data
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


config_cnx_test_data_400: list[ConfigurationConnection] = [
    {
        "authentication_connections": {
            "type": "all",
            "connection_types": ["ldap", "saml"],
        },
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
        "authentication_connections": {
            "type": "all",
            "connection_types": ["ldap", "saml"],
        },
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
        "authentication_connections": {
            "type": "all",
            "connection_types": ["ldap", "saml"],
        },
        "user_sync": {
            "sync_with_ldap_connections": "all",
        },
        "replicate_event_console": True,
        "replicate_extensions": True,
    },
]


@pytest.mark.parametrize("data", config_cnx_test_data_400)
def test_update_configuration_connection_400(  # type: ignore[misc]
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


def test_update_status_host_200(clients: ClientRegistry) -> None:
    clients.HostConfig.create(host_name="host1", folder="/")
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)
    data: StatusHost = {"status_host_set": "enabled", "site": "NO_SITE", "host": "host1"}
    config["status_connection"]["status_host"] = data
    resp = clients.SiteManagement.update(site_id=site_id, site_config=config)
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


status_host_test_data: list[StatusHost] = [
    {"status_host_set": "disabled", "site": "NO_SITE", "host": "host1"},
    {"status_host_set": "enabled", "site": "NO_SITE"},
    {"status_host_set": "enabled", "host": "host1"},
]


@pytest.mark.parametrize("data", status_host_test_data)
def test_update_status_host_400(clients: ClientRegistry, data: StatusHost) -> None:
    clients.HostConfig.create(host_name="host1", folder="/")
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
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


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
    extensions = resp.json["extensions"]
    extensions.pop("logged_in", None)
    assert extensions == config


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
    if version.edition(paths.omd_root) is version.Edition.ULTIMATEMT:
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
            "authentication_connections": {
                "type": "all",
                "connection_types": ["ldap", "saml"],
            },
            "user_sync": {"sync_with_ldap_connections": "all"},
            "replicate_event_console": True,
            "replicate_extensions": True,
            "message_broker_port": 5672,
            "is_trusted": False,
        },
    }
    if version.edition(paths.omd_root) is version.Edition.ULTIMATEMT:
        r["basic_settings"]["customer"] = "provider"

    clients.SiteManagement.create(site_config=r)


def test_create_no_sync_site_connection(clients: ClientRegistry) -> None:
    config, site_id = _default_config_with_site_id()
    config["configuration_connection"]["enable_replication"] = False
    clients.SiteManagement.create(site_config=config)

    resp = clients.SiteManagement.get(site_id=site_id)
    assert resp.json["extensions"]["configuration_connection"] == config["configuration_connection"]


def test_remote_site_logged_in(clients: ClientRegistry, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.gui.fields.definitions.load_users", lambda: ["cmkadmin"])
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.do_site_login",
        lambda site_id, username, password, debug: "watosecret",
    )
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.trigger_remote_certs_creation",
        lambda site_id, settings, force, debug: None,
    )
    config, site_id = _default_config_with_site_id()
    clients.SiteManagement.create(site_config=config)

    clients.SiteManagement.login(site_id=site_id, username="cmkadmin", password="cmk")
    assert clients.SiteManagement.get(site_id=site_id).json["extensions"]["logged_in"]


def test_remote_site_not_logged_in(clients: ClientRegistry) -> None:
    config, _site_id = _default_config_with_site_id()
    assert not clients.SiteManagement.create(site_config=config).json["extensions"]["logged_in"]


def test_main_site_no_logged_in(clients: ClientRegistry) -> None:
    assert "logged_in" not in clients.SiteManagement.get(site_id="NO_SITE").json["extensions"]
