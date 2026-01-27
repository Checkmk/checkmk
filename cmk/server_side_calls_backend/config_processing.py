#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel

from cmk.password_store.v1_unstable import Secret as StoreSecret
from cmk.server_side_calls import internal, v1
from cmk.utils import config_warnings

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


type _PasswordSpec = tuple[
    Literal["cmk_postprocessed"], Literal["stored_password", "explicit_password"], tuple[str, str]
]


class BackendProxyAuth(BaseModel):
    user: str
    password: _PasswordSpec


class BackendProxy(BaseModel):
    scheme: str
    proxy_server_name: str
    port: int
    auth: BackendProxyAuth | None = None

    def url(self, password_lookup: Callable[[str], str | None], usage_hint: str) -> str:
        if (
            self.auth is None
            or (secret := self._secret(self.auth, password_lookup, usage_hint)) is None
        ):
            return f"{self.scheme}://{self.proxy_server_name}:{self.port}"
        return self._make_url_with_auth(self.auth.user, secret)

    def _secret(
        self, auth: BackendProxyAuth, password_lookup: Callable[[str], str | None], usage_hint: str
    ) -> str | None:
        _, password_type, (secret_id, secret_value) = auth.password
        match password_type:
            case "stored_password":
                if (password := password_lookup(secret_id)) is None:
                    config_warnings.warn(
                        f'The stored password "{secret_id}" ({usage_hint}) does not exist.'
                    )
                return password
            case "explicit_password":
                return secret_value

    def _make_url_with_auth(self, user: str, password: str) -> str:
        return f"{self.scheme}://{user}:{password}@{self.proxy_server_name}:{self.port}"


type GlobalProxies = Mapping[str, BackendProxy]


@dataclass(frozen=True)
class GlobalProxiesWithLookup:
    global_proxies: GlobalProxies
    password_lookup: Callable[[str], str | None]


OAuth2ConnectorType = Literal["microsoft_entra_id"]


@dataclass(frozen=True)
class OAuth2Connection:
    title: str
    client_secret: _PasswordSpec
    access_token: _PasswordSpec
    refresh_token: _PasswordSpec
    client_id: str
    tenant_id: str
    authority: str
    connector_type: OAuth2ConnectorType


def extract_all_adhoc_secrets(
    rules_by_name: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    global_proxies_with_lookup: GlobalProxiesWithLookup,
    oauth2_connections: Mapping[str, OAuth2Connection],
) -> Mapping[str, StoreSecret[str]]:
    """
    >>> extract_all_adhoc_secrets(
    ...     rules_by_name=[
    ...         (
    ...             'pure_storage_fa',
    ...             [
    ...                 {
    ...                     'api_token': ('cmk_postprocessed','explicit_password', (':uuid:1234', 'knubblwubbl')),
    ...                     'timeout': 5.0,
    ...                 },
    ...             ],
    ...         ),
    ...     ],
    ...     global_proxies_with_lookup=GlobalProxiesWithLookup(
    ...         global_proxies={},
    ...         password_lookup=lambda name: None,
    ...     ),
    ...     oauth2_connections={},
    ... )
    {':uuid:1234': Secret('****')}
    """
    use_alpha = True  # whatever is more comprehensive in extracting secrets
    preprocessing_results = [
        (
            name,
            [
                process_configuration_to_parameters(
                    rule,
                    global_proxies_with_lookup,
                    oauth2_connections,
                    f"ruleset: {name}",
                    use_alpha,
                )
                for rule in rules
            ],
        )
        for name, rules in rules_by_name
    ]

    return {
        k: v
        for name, prep in preprocessing_results
        for res in prep
        for k, v in res.found_secrets.items()
    }


_RuleSetType_co = TypeVar("_RuleSetType_co", covariant=True)


@dataclass(frozen=True)
class ReplacementResult(Generic[_RuleSetType_co]):
    value: _RuleSetType_co  # type: ignore[misc]
    found_secrets: Mapping[str, StoreSecret[str]]
    surrogates: Mapping[int, str]


def process_configuration_to_parameters(
    params: Mapping[str, object],
    global_proxies_with_lookup: GlobalProxiesWithLookup,
    oauth2_connections: Mapping[str, OAuth2Connection],
    usage_hint: str,
    is_internal: bool,
) -> ReplacementResult[Mapping[str, object]]:
    d_results = [
        (
            k,
            _processed_config_value(
                v, global_proxies_with_lookup, oauth2_connections, usage_hint, is_internal
            ),
        )
        for k, v in params.items()
    ]
    return ReplacementResult(
        value={k: res.value for k, res in d_results},
        found_secrets={k: v for _, res in d_results for k, v in res.found_secrets.items()},
        surrogates={k: v for _, res in d_results for k, v in res.surrogates.items()},
    )


def _processed_config_value(
    params: object,
    global_proxies_with_lookup: GlobalProxiesWithLookup,
    oauth2_connections: Mapping[str, OAuth2Connection],
    usage_hint: str,
    is_internal: bool,
) -> ReplacementResult[object]:
    match params:
        case list():
            results = [
                _processed_config_value(
                    v, global_proxies_with_lookup, oauth2_connections, usage_hint, is_internal
                )
                for v in params
            ]
            return ReplacementResult(
                value=[res.value for res in results],
                found_secrets={k: v for res in results for k, v in res.found_secrets.items()},
                surrogates={k: v for res in results for k, v in res.surrogates.items()},
            )
        case tuple(
            (
                "cmk_postprocessed",
                "stored_password" | "explicit_password" as secret_type,
                (str() as secret_id, str() as secret_value),
            )
        ):
            return _replace_password(
                secret_id,
                StoreSecret(secret_value) if secret_type == "explicit_password" else None,
                is_internal=is_internal,
            )
        case tuple(
            (
                "cmk_postprocessed",
                "oauth2_connection",
                str() as connection_id,
            )
        ):
            return _replace_oauth2_connection(connection_id, oauth2_connections)

        case tuple(("cmk_postprocessed", str() as special_type, value)):
            match special_type, value, is_internal:
                case ("no_proxy", str(), bool()):
                    return ReplacementResult(
                        internal.NoProxy() if is_internal else v1.NoProxy(), {}, {}
                    )
                case ("environment_proxy", str(), bool()):
                    return ReplacementResult(
                        internal.EnvProxy() if is_internal else v1.EnvProxy(), {}, {}
                    )
                case ("stored_proxy", str(proxy_name), True):
                    return _replace_internal_stored_proxy(
                        proxy_name, global_proxies_with_lookup, usage_hint
                    )
                case ("stored_proxy", str(proxy_name), False):
                    return _replace_v1_stored_proxy(
                        proxy_name, global_proxies_with_lookup, usage_hint
                    )
                case ("explicit_proxy", str() | Mapping() as proxy_spec, True):
                    return _replace_internal_explicit_proxy(proxy_spec)
                case ("explicit_proxy", str() | Mapping() as proxy_spec, False):
                    return _replace_v1_explicit_proxy(proxy_spec)
                case _:
                    raise ValueError(
                        f"Unknown special config processing type: {special_type} with value {value}"
                    )

        case tuple():
            results = [
                _processed_config_value(
                    v, global_proxies_with_lookup, oauth2_connections, usage_hint, is_internal
                )
                for v in params
            ]
            return ReplacementResult(
                value=tuple(res.value for res in results),
                found_secrets={k: v for res in results for k, v in res.found_secrets.items()},
                surrogates={k: v for res in results for k, v in res.surrogates.items()},
            )
        case dict():
            return process_configuration_to_parameters(
                params, global_proxies_with_lookup, oauth2_connections, usage_hint, is_internal
            )
        case other:
            return ReplacementResult(value=other, found_secrets={}, surrogates={})


def _replace_password(
    name: str,
    value: StoreSecret[str] | None,
    is_internal: bool,
) -> ReplacementResult[internal.Secret | v1.Secret]:
    # We need some injective function.
    surrogate = id(name)
    return ReplacementResult(
        value=(internal.Secret if is_internal else v1.Secret)(surrogate),
        found_secrets={} if value is None else {name: value},
        surrogates={surrogate: name},
    )


def _replace_oauth2_connection(
    connection_id: str, oauth2_connections: Mapping[str, OAuth2Connection]
) -> ReplacementResult[internal.OAuth2Connection]:
    try:
        oauth2_connection = oauth2_connections[connection_id]
    except KeyError:
        config_warnings.warn(f'The OAuth2 connection "{connection_id}" does not exist.')
        return ReplacementResult(
            internal.OAuth2Connection(
                client_secret=v1.Secret(id(0)),
                access_token=v1.Secret(id(0)),
                refresh_token=v1.Secret(id(0)),
                client_id="",
                tenant_id="",
                authority="",
                connector_type="",
            ),
            {},
            {},
        )
    _replaced_client_secret = _replace_password(oauth2_connection.client_secret[2][0], None, True)
    _replaced_access_token = _replace_password(oauth2_connection.access_token[2][0], None, True)
    _replaced_refresh_token = _replace_password(oauth2_connection.refresh_token[2][0], None, True)
    return ReplacementResult(
        internal.OAuth2Connection(
            client_secret=_replaced_client_secret.value,
            access_token=_replaced_access_token.value,
            refresh_token=_replaced_refresh_token.value,
            client_id=oauth2_connection.client_id,
            tenant_id=oauth2_connection.tenant_id,
            authority=oauth2_connection.authority,
            connector_type=oauth2_connection.connector_type,
        ),
        {
            **_replaced_client_secret.found_secrets,
            **_replaced_access_token.found_secrets,
            **_replaced_refresh_token.found_secrets,
        },
        {
            **_replaced_client_secret.surrogates,
            **_replaced_access_token.surrogates,
            **_replaced_refresh_token.surrogates,
        },
    )


def _replace_v1_stored_proxy(
    proxy_name: str,
    global_proxies_with_lookup: GlobalProxiesWithLookup,
    usage_hint: str,
) -> ReplacementResult[v1.EnvProxy | v1.URLProxy]:
    try:
        global_proxy = global_proxies_with_lookup.global_proxies[proxy_name]
    except KeyError:
        config_warnings.warn(f'The global proxy "{proxy_name}" ({usage_hint}) does not exist.')
        return ReplacementResult(v1.EnvProxy(), {}, {})

    return ReplacementResult(
        v1.URLProxy(url=global_proxy.url(global_proxies_with_lookup.password_lookup, usage_hint)),
        {},
        {},
    )


def _replace_v1_explicit_proxy(
    proxy_spec: Mapping[str, object] | str,
) -> ReplacementResult[v1.EnvProxy | v1.URLProxy]:
    match proxy_spec:
        case str():
            return ReplacementResult(v1.URLProxy(url=proxy_spec), {}, {})
        case {"scheme": scheme, "proxy_server_name": server_name, "port": port}:
            return ReplacementResult(v1.URLProxy(url=f"{scheme}://{server_name}:{port}"), {}, {})
        case _:
            return ReplacementResult(internal.EnvProxy(), {}, {})


def _replace_internal_stored_proxy(
    proxy_name: str,
    global_proxies_with_lookup: GlobalProxiesWithLookup,
    usage_hint: str,
) -> ReplacementResult[internal.EnvProxy | internal.URLProxy]:
    try:
        global_proxy = global_proxies_with_lookup.global_proxies[proxy_name]
    except KeyError:
        config_warnings.warn(f'The global proxy "{proxy_name}" ({usage_hint}) does not exist.')
        return ReplacementResult(internal.EnvProxy(), {}, {})

    if global_proxy.auth is not None:
        _replaced_password = _replace_password(
            name=global_proxy.auth.password[2][0],
            value=None
            if global_proxy.auth.password[1] == "stored_password"
            else StoreSecret(global_proxy.auth.password[2][1]),
            is_internal=True,
        )

        return ReplacementResult(
            internal.URLProxy(
                scheme=global_proxy.scheme,
                proxy_server_name=global_proxy.proxy_server_name,
                port=global_proxy.port,
                auth=internal.URLProxyAuth(
                    user=global_proxy.auth.user,
                    password=_replaced_password.value,
                ),
            ),
            _replaced_password.found_secrets,
            _replaced_password.surrogates,
        )

    return ReplacementResult(
        internal.URLProxy(
            scheme=global_proxy.scheme,
            proxy_server_name=global_proxy.proxy_server_name,
            port=global_proxy.port,
            auth=None,
        ),
        {},
        {},
    )


def _replace_internal_explicit_proxy(
    proxy_spec: Mapping[str, object] | str,
) -> ReplacementResult[internal.EnvProxy | internal.URLProxy]:
    match proxy_spec:
        case str():
            parsed_url = urlparse(proxy_spec)
            if parsed_url.hostname is None or parsed_url.port is None:
                return ReplacementResult(internal.EnvProxy(), {}, {})

            if parsed_url.username is not None and parsed_url.password is not None:
                config_warnings.warn(
                    "Explicit proxy URLs with embedded authentication are not supported."
                )

            return ReplacementResult(
                internal.URLProxy(
                    parsed_url.scheme,
                    parsed_url.hostname,
                    parsed_url.port,
                    auth=None,
                ),
                {},
                {},
            )

        case {
            "scheme": str() as scheme,
            "proxy_server_name": str() as name,
            "port": int() as port,
            "auth": {
                "user": str() as user,
                "password": (
                    "cmk_postprocessed",
                    "stored_password" | "explicit_password" as password_type,
                    (str(part1), str(part2)),
                ),
            },
        }:
            _replaced_password = _replace_password(
                name=part1,
                value=None if password_type == "stored_password" else StoreSecret(part2),
                is_internal=True,
            )

            return ReplacementResult(
                internal.URLProxy(
                    scheme=scheme,
                    proxy_server_name=name,
                    port=port,
                    auth=internal.URLProxyAuth(
                        user=user,
                        password=_replaced_password.value,
                    ),
                ),
                _replaced_password.found_secrets,
                _replaced_password.surrogates,
            )

        case {"scheme": str() as scheme, "proxy_server_name": str() as name, "port": int() as port}:
            return ReplacementResult(
                internal.URLProxy(scheme=scheme, proxy_server_name=name, port=port), {}, {}
            )

        case _:
            raise ValueError(f"Unknown explicit proxy specification: {proxy_spec}")
