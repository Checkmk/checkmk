#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.password_store.v1_unstable import Secret
from cmk.server_side_calls import internal, v1
from cmk.server_side_calls_backend.config_processing import (
    BackendProxy,
    GlobalProxiesWithLookup,
    OAuth2Connection,
    process_configuration_to_parameters,
    ReplacementResult,
)


def test_process_configuration_to_parameter_password_stored() -> None:
    assert process_configuration_to_parameters(
        params={"password": ("cmk_postprocessed", "stored_password", ("my_secret_id", ""))},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"password": v1.Secret(id("my_secret_id"))},
        found_secrets={},
        surrogates={id("my_secret_id"): "my_secret_id"},
    )


def test_process_configuration_to_parameter_password_explicit() -> None:
    assert process_configuration_to_parameters(
        params={
            "password": ("cmk_postprocessed", "explicit_password", (":uuid:1234", "actual_secret"))
        },
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"password": v1.Secret(id(":uuid:1234"))},
        found_secrets={":uuid:1234": Secret("actual_secret")},
        surrogates={id(":uuid:1234"): ":uuid:1234"},
    )


def test_process_configuration_to_parameter_no_proxy_v1() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "no_proxy", "")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"proxy": v1.NoProxy()},
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_env_proxy_v1() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "environment_proxy", "")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={}, password_lookup=lambda x: None
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"proxy": v1.EnvProxy()},
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_explicit_proxy_v1() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "explicit_proxy", "hurray.com")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"proxy": v1.URLProxy("url_proxy", "hurray.com")},
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_global_proxy_ok_v1() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "stored_proxy", "my_global_proxy")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={
                "my_global_proxy": BackendProxy(
                    scheme="http",
                    proxy_server_name="proxy.example.com",
                    port=3128,
                ),
            },
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"proxy": v1.URLProxy("url_proxy", "http://proxy.example.com:3128")},
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_global_proxy_missing_v1() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "stored_proxy", "my_global_proxy")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"proxy": v1.EnvProxy()},
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_no_proxy_internal() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "no_proxy", "")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"proxy": internal.NoProxy()},
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_env_proxy_internal() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "environment_proxy", "")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"proxy": internal.EnvProxy()},
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_explicit_proxy_internal() -> None:
    assert process_configuration_to_parameters(
        params={
            "proxy": (
                "cmk_postprocessed",
                "explicit_proxy",
                {"scheme": "http", "proxy_server_name": "hurray.com", "port": 6532},
            )
        },
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=True,
    ) == ReplacementResult(
        value={
            "proxy": internal.URLProxy(
                scheme="http", proxy_server_name="hurray.com", port=6532, auth=None
            )
        },
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_global_proxy_ok_internal() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "stored_proxy", "my_global_proxy")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={
                "my_global_proxy": BackendProxy(
                    scheme="http",
                    proxy_server_name="proxy.example.com",
                    port=3128,
                ),
            },
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=True,
    ) == ReplacementResult(
        value={
            "proxy": internal.URLProxy(
                scheme="http",
                proxy_server_name="proxy.example.com",
                port=3128,
                auth=None,
            )
        },
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_global_proxy_missing_internal() -> None:
    assert process_configuration_to_parameters(
        params={"proxy": ("cmk_postprocessed", "stored_proxy", "my_global_proxy")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={},
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={"proxy": internal.EnvProxy()},
        found_secrets={},
        surrogates={},
    )


def test_process_configuration_to_parameter_oauth2_connection() -> None:
    assert process_configuration_to_parameters(
        params={"auth": ("cmk_postprocessed", "oauth2_connection", "my_oauth2_connection")},
        global_proxies_with_lookup=GlobalProxiesWithLookup(
            global_proxies={},
            password_lookup=lambda x: None,
        ),
        oauth2_connections={
            "my_oauth2_connection": OAuth2Connection(
                title="My OAuth",
                client_secret=("cmk_postprocessed", "stored_password", ("1", "")),
                access_token=("cmk_postprocessed", "stored_password", ("2", "")),
                refresh_token=("cmk_postprocessed", "stored_password", ("3", "")),
                client_id="client_id_value",
                tenant_id="tenant_id_value",
                authority="global",
                connector_type="microsoft_entra_id",
            )
        },
        usage_hint="test",
        is_internal=False,
    ) == ReplacementResult(
        value={
            "auth": internal.OAuth2Connection(
                client_secret=v1.Secret(id("1")),
                access_token=v1.Secret(id("2")),
                refresh_token=v1.Secret(id("3")),
                client_id="client_id_value",
                tenant_id="tenant_id_value",
                authority="global",
                connector_type="microsoft_entra_id",
            )
        },
        found_secrets={},
        surrogates={id("1"): "1", id("2"): "2", id("3"): "3"},
    )
