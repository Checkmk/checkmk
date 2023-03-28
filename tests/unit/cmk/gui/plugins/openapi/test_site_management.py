#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Mapping
from functools import partial
from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import version

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.openapi.endpoints.site_management.common import (
    default_config_example as _default_config,
)

DOMAIN_TYPE = "site_connection"


@pytest.fixture(name="object_base")
def user_role_object_base(base: str) -> str:
    return f"{base}/objects/{DOMAIN_TYPE}/"


@pytest.fixture(name="collection_base")
def user_role_collection_base(base: str) -> str:
    return f"{base}/domain-types/{DOMAIN_TYPE}/collections/all"


@pytest.fixture(name="get_site")
def partial_get(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.get,
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="get_sites")
def partial_list(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.get,
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="post_site")
def partial_post(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="delete_site")
def partial_delete(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        status=204,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="logout_site")
def partial_logout(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        status=204,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="put_site")
def partial_put(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.put,
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


def test_get_a_site(get_site: Callable, object_base: str) -> None:
    site_id = "NO_SITE"
    resp = get_site(url=f"{object_base}{site_id}")
    assert resp.json["domainType"] == DOMAIN_TYPE
    assert resp.json["id"] == site_id

    example_config = _default_config()["site_config"]
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


def test_get_a_site_that_doesnt_exist(get_site: Callable, object_base: str) -> None:
    get_site(url=object_base + "NO_EXIST_SITE", status=404)


def test_get_sites(get_sites: Callable, collection_base: str) -> None:
    resp = get_sites(url=collection_base)
    assert resp.json["domainType"] == DOMAIN_TYPE
    assert resp.json["value"][0]["id"] == "NO_SITE"


def test_site_login(post_site: Callable, object_base: str, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.restful_objects.request_schemas.load_users", lambda: ["cmkadmin"]
    )
    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.do_site_login",
        lambda site_id, username, password: "watosecret",
    )
    site_id = "NO_SITE"
    post_site(
        status=204,
        url=f"{object_base}{site_id}/actions/login/invoke",
        params=json.dumps({"username": "cmkadmin", "password": "cmk"}),
    )


def test_site_login_site_doesnt_exist(
    post_site: Callable, object_base: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.restful_objects.request_schemas.load_users", lambda: ["cmkadmin"]
    )
    site_id = "NO_EXIST_SITE"
    post_site(
        status=404,
        url=f"{object_base}{site_id}/actions/login/invoke",
        params=json.dumps({"username": "cmkadmin", "password": "cmk"}),
    )


def test_site_login_problem(
    post_site: Callable, object_base: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.restful_objects.request_schemas.load_users", lambda: ["cmkadmin"]
    )

    class MockLoginException:
        def __init__(self, *args, **kwargs):
            raise Exception("There was a problem logging in.")

    monkeypatch.setattr(
        "cmk.gui.watolib.site_management.do_site_login",
        MockLoginException,
    )

    site_id = "NO_SITE"
    post_site(
        status=400,
        url=f"{object_base}{site_id}/actions/login/invoke",
        params=json.dumps({"username": "cmkadmin", "password": "cmk"}),
    )


def test_logout_site(logout_site: Callable, object_base: str) -> None:
    site_id = "NO_SITE"
    logout_site(url=f"{object_base}{site_id}/actions/logout/invoke")


def test_logout_site_that_doesnt_exist(post_site: Callable, object_base: str) -> None:
    site_id = "NO_EXIST_SITE"
    post_site(url=f"{object_base}{site_id}/actions/logout/invoke", status=404)


def test_site_delete(
    post_site: Callable, delete_site: Callable, object_base: str, collection_base: str
) -> None:
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(_default_config()))
    delete_site(url=f"{object_base}{site_id}/actions/delete/invoke")


def test_site_delete_problem(
    post_site: Callable, object_base: str, collection_base: str, monkeypatch: MonkeyPatch
) -> None:
    class MockDeleteException:
        def __init__(self, *args, **kwargs):
            raise MKUserError(varname=None, message="There was a problem deleting that site.")

    monkeypatch.setattr(
        "cmk.gui.watolib.sites.SiteManagement.delete_site",
        MockDeleteException,
    )
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(_default_config()))
    post_site(url=f"{object_base}{site_id}/actions/delete/invoke", status=404)


def test_site_post(post_site: Callable, collection_base: str) -> None:
    post_site(url=collection_base, params=json.dumps(_default_config()))


def test_site_post_site_already_exists(post_site: Callable, collection_base: str) -> None:
    post_site(url=collection_base, params=json.dumps(_default_config()))
    post_site(url=collection_base, params=json.dumps(_default_config()), status=400)


keys_to_remove = ("basic_settings", "status_connection", "configuration_connection")


@pytest.mark.parametrize("key", keys_to_remove)
def test_site_post_site_missing_settings(
    key: str, post_site: Callable, collection_base: str
) -> None:
    config = _default_config()
    config["site_config"].pop(key)  # type: ignore
    post_site(url=collection_base, params=json.dumps(config), status=400)


def test_post_then_get_site(
    post_site: Callable, collection_base: str, object_base: str, get_site: Callable
) -> None:
    site_id = "site_id_1"
    siteconfig = _default_config()
    post_site(url=collection_base, params=json.dumps(siteconfig))
    resp = get_site(url=f"{object_base}{site_id}")
    assert resp.json["extensions"] == siteconfig["site_config"]


def test_put_site(
    post_site: Callable, put_site: Callable, collection_base: str, object_base: str
) -> None:
    site_id = "site_id_1"
    siteconfig = _default_config()
    post_site(url=collection_base, params=json.dumps(siteconfig))
    resp = put_site(url=f"{object_base}{site_id}", params=json.dumps(siteconfig))
    assert resp.json["extensions"] == siteconfig["site_config"]


def test_put_site_when_doesnt_exist(put_site: Callable, object_base: str) -> None:
    site_id = "site_id_1"
    siteconfig = _default_config()
    put_site(url=f"{object_base}{site_id}", params=json.dumps(siteconfig), status=404)


def test_put_update_alias(
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
    get_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["basic_settings"]["alias"] = "edited alias"
    put_site(url=f"{object_base}{site_id}", params=json.dumps(config))
    resp = get_site(url=f"{object_base}{site_id}")
    assert resp.json["extensions"]["basic_settings"]["alias"] == "edited alias"


connection_test_data_200 = (
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
)

connection_test_data_400 = (
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
    {"socket_type": "electrical_socket"},
    {"socket_type": "unix"},
    {"socket_type": "tcp"},
    {"socket_type": "tcp6"},
    {"socket_type": "tcp6", "host": "5402:1db8:95a3:NOPE:9a2e:0480:8334"},
    {"socket_type": "tcp6", "host": "5402:1db8:95a3:0000:0000:9a2e:0480:8334", "port": 123456},
    {"host": "192.168.1.200", "port": 1234512345, "encrypted": False, "verify": False},
)


@pytest.mark.parametrize("data", connection_test_data_200)
def test_put_update_connection_200(
    data: Mapping[str, Any],
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["status_connection"]["connection"] = data
    resp = put_site(url=f"{object_base}{site_id}", params=json.dumps(config))
    assert resp.json["extensions"]["status_connection"]["connection"] == data


@pytest.mark.parametrize("data", connection_test_data_400)
def test_put_update_connection_400(
    data: Mapping[str, Any],
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["status_connection"]["connection"] = data
    put_site(url=f"{object_base}{site_id}", params=json.dumps(config), status=400)


proxy_test_data_200 = (
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
)

proxy_test_data_400 = (
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
        "params": {"invalid_param": True},
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
)


@pytest.mark.parametrize("data", proxy_test_data_200)
def test_put_update_proxy_200(
    data: Mapping[str, Any],
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["status_connection"]["proxy"] = data
    resp = put_site(url=f"{object_base}{site_id}", params=json.dumps(config))
    assert resp.json["extensions"]["status_connection"]["proxy"] == data


@pytest.mark.parametrize("data", proxy_test_data_400)
def test_put_update_proxy_400(
    data: Mapping[str, Any],
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["status_connection"]["proxy"] = data
    put_site(url=f"{object_base}{site_id}", params=json.dumps(config), status=400)


def test_put_disable_user_sync(
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
    get_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    edited_user_sync = {"sync_with_ldap_connections": "disabled"}
    config["site_config"]["configuration_connection"]["user_sync"] = edited_user_sync
    put_site(url=f"{object_base}{site_id}", params=json.dumps(config))
    resp = get_site(url=f"{object_base}{site_id}")
    assert resp.json["extensions"]["configuration_connection"]["user_sync"] == edited_user_sync


def test_put_user_sync_with_ldap_connections_200(
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.utils.connection_choices",
        lambda: [
            ("LDAP_1", "LDAP_1 (ldap)"),
            ("LDAP_2", "LDAP_2 (ldap)"),
            ("LDAP_3", "LDAP_3 (ldap)"),
        ],
    )

    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    edited_user_sync = {
        "sync_with_ldap_connections": "ldap",
        "ldap_connections": ["LDAP_1", "LDAP_2", "LDAP_3"],
    }
    config["site_config"]["configuration_connection"]["user_sync"] = edited_user_sync
    resp = put_site(url=f"{object_base}{site_id}", params=json.dumps(config))
    assert resp.json["extensions"]["configuration_connection"]["user_sync"] == edited_user_sync


def test_put_user_sync_with_ldap_connections_400(
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:

    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    edited_user_sync = {
        "sync_with_ldap_connections": "ldap",
        "ldap_connections": ["LDAP_1", "LDAP_2", "LDAP_4"],
    }
    config["site_config"]["configuration_connection"]["user_sync"] = edited_user_sync
    put_site(url=f"{object_base}{site_id}", params=json.dumps(config), status=400)


config_cnx_test_data_200 = (
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
    },
    {
        "enable_replication": False,
        "url_of_remote_site": "https://localhost/heute_remote_site_id_1/check_mk/",
        "disable_remote_configuration": False,
        "ignore_tls_errors": False,
        "direct_login_to_web_gui_allowed": False,
        "user_sync": {
            "sync_with_ldap_connections": "all",
        },
        "replicate_event_console": False,
        "replicate_extensions": False,
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
    },
)

config_cnx_test_data_400 = (
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
        "invalid_attribute": True,
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
)


@pytest.mark.parametrize("data", config_cnx_test_data_200)
def test_put_configuration_connection_200(
    data: dict[str, Any],
    post_site: Callable,
    collection_base: str,
    object_base: str,
    put_site: Callable,
) -> None:

    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["configuration_connection"] = data
    resp = put_site(url=f"{object_base}{site_id}", params=json.dumps(config))
    assert resp.json["extensions"]["configuration_connection"] == data


@pytest.mark.parametrize("data", config_cnx_test_data_400)
def test_put_configuration_connection_400(
    data: dict[str, Any],
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:

    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["configuration_connection"] = data
    put_site(url=f"{object_base}{site_id}", params=json.dumps(config), status=400)


status_host_test_data = (
    ({"status_host_set": "enabled", "site": "NO_SITE", "host": "host1"}, 200),
    ({"status_host_set": "disabled", "site": "NO_SITE", "host": "host1"}, 400),
    ({"status_host_set": "enabled", "site": "NO_SITE"}, 400),
    ({"status_host_set": "enabled", "host": "host1"}, 400),
)


@pytest.mark.parametrize("data, status_code", status_host_test_data)
def test_put_status_host(
    data: Mapping[str, Any],
    status_code: int,
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
    monkeypatch: MonkeyPatch,
) -> None:
    class MockHost:
        @classmethod
        def host(cls, *args: Any) -> bool:
            return True

    monkeypatch.setattr("cmk.gui.fields.definitions.Host", MockHost)

    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))

    config["site_config"]["status_connection"]["status_host"] = data
    resp = put_site(url=f"{object_base}{site_id}", params=json.dumps(config), status=status_code)
    if status_code == 200:
        assert resp.json["extensions"]["status_connection"]["status_host"] == data


url_of_remote_site_test_data_200 = (
    "http://localhost/abc/check_mk/",
    "https://localhost/abc/check_mk/",
)
url_of_remote_site_test_data_400 = (
    "http://localhost/abc/123",
    "https://localhost/abc/123",
    "http//localhost/abc/123",
    "https:localhost/abc/123",
    "httpss://localhost/abc/123",
    "htttp://localhost/abc/123",
)


@pytest.mark.parametrize("data", url_of_remote_site_test_data_200)
def test_put_update_url_of_remote_site_200(
    data: Mapping[str, Any],
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["configuration_connection"]["url_of_remote_site"] = data
    resp = put_site(url=f"{object_base}{site_id}", params=json.dumps(config))
    assert resp.json["extensions"]["configuration_connection"]["url_of_remote_site"] == data


@pytest.mark.parametrize("data", url_of_remote_site_test_data_400)
def test_put_update_url_of_remote_site_400(
    data: Mapping[str, Any],
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))
    config["site_config"]["configuration_connection"]["url_of_remote_site"] = data
    put_site(url=f"{object_base}{site_id}", params=json.dumps(config), status=400)


def test_put_update_url_prefix_200(
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))

    config["site_config"]["status_connection"]["url_prefix"] = "/remote_site_1/"
    resp = put_site(url=f"{object_base}{site_id}", params=json.dumps(config))
    assert resp.json["extensions"]["status_connection"]["url_prefix"] == "/remote_site_1/"


def test_put_update_url_prefix_400(
    post_site: Callable,
    object_base: str,
    collection_base: str,
    put_site: Callable,
) -> None:
    config = _default_config()
    site_id = "site_id_1"
    post_site(url=collection_base, params=json.dumps(config))

    config["site_config"]["status_connection"]["url_prefix"] = "/remote_site_1"
    put_site(url=f"{object_base}{site_id}", params=json.dumps(config), status=400)


def test_post_site_config_customer_field(
    post_site: Callable,
    collection_base: str,
) -> None:
    config = _default_config()
    if version.is_managed_edition():
        r = post_site(url=collection_base, params=json.dumps(config), status=200)
        assert "customer" in r.json["extensions"]["basic_settings"]
        del config["site_config"]["basic_settings"]["customer"]
        post_site(url=collection_base, params=json.dumps(config), status=400)

    else:
        r = post_site(url=collection_base, params=json.dumps(config), status=200)
        assert "customer" not in r.json["extensions"]["basic_settings"]
        config["site_config"]["basic_settings"].update({"customer": "provider"})
        post_site(url=collection_base, params=json.dumps(config), status=400)
