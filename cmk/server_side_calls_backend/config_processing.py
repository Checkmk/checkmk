#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

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


def extract_all_adhoc_secrets(
    rules_by_name: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    global_proxies_with_lookup: GlobalProxiesWithLookup,
) -> Mapping[str, str]:
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
    ... )
    {':uuid:1234': 'knubblwubbl'}
    """
    use_alpha = True  # whatever is more comprehensive in extracting secrets
    preprocessing_results = [
        (
            name,
            [
                process_configuration_to_parameters(
                    rule, global_proxies_with_lookup, f"ruleset: {name}", use_alpha
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
    value: _RuleSetType_co
    found_secrets: Mapping[str, str]
    surrogates: Mapping[int, str]


def process_configuration_to_parameters(
    params: Mapping[str, object],
    global_proxies_with_lookup: GlobalProxiesWithLookup,
    usage_hint: str,
    is_internal: bool,
) -> ReplacementResult[Mapping[str, object]]:
    d_results = [
        (k, _processed_config_value(v, global_proxies_with_lookup, usage_hint, is_internal))
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
    usage_hint: str,
    is_internal: bool,
) -> ReplacementResult[object]:
    match params:
        case list():
            results = [
                _processed_config_value(v, global_proxies_with_lookup, usage_hint, is_internal)
                for v in params
            ]
            return ReplacementResult(
                value=[res.value for res in results],
                found_secrets={k: v for res in results for k, v in res.found_secrets.items()},
                surrogates={k: v for res in results for k, v in res.surrogates.items()},
            )
        case tuple():
            match params:
                case ("cmk_postprocessed", "stored_password", value):
                    return _replace_password(value[0], None, is_internal=is_internal)
                case ("cmk_postprocessed", "explicit_password", value):
                    return _replace_password(value[0], value[1], is_internal=is_internal)
                case ("cmk_postprocessed", "no_proxy", str()):
                    return ReplacementResult(
                        internal.NoProxy() if is_internal else v1.NoProxy(), {}, {}
                    )
                case ("cmk_postprocessed", "environment_proxy", str()):
                    return ReplacementResult(
                        internal.EnvProxy() if is_internal else v1.EnvProxy(), {}, {}
                    )
                case (
                    "cmk_postprocessed",
                    "stored_proxy" | "explicit_proxy" as proxy_type,
                    str(proxy_spec),
                ):
                    return (
                        _replace_alpha_url_proxies(
                            proxy_type, proxy_spec, global_proxies_with_lookup, usage_hint
                        )
                        if is_internal
                        else _replace_v1_url_proxies(
                            proxy_type, proxy_spec, global_proxies_with_lookup, usage_hint
                        )
                    )
                case _:
                    results = [
                        _processed_config_value(
                            v, global_proxies_with_lookup, usage_hint, is_internal
                        )
                        for v in params
                    ]
                    return ReplacementResult(
                        value=tuple(res.value for res in results),
                        found_secrets={
                            k: v for res in results for k, v in res.found_secrets.items()
                        },
                        surrogates={k: v for res in results for k, v in res.surrogates.items()},
                    )
        case dict():
            return process_configuration_to_parameters(
                params, global_proxies_with_lookup, usage_hint, is_internal
            )
        case other:
            return ReplacementResult(value=other, found_secrets={}, surrogates={})


def _replace_password(
    name: str,
    value: str | None,
    is_internal: bool,
) -> ReplacementResult[internal.Secret | v1.Secret]:
    # We need some injective function.
    surrogate = id(name)
    return ReplacementResult(
        value=(internal.Secret if is_internal else v1.Secret)(surrogate),
        found_secrets={} if value is None else {name: value},
        surrogates={surrogate: name},
    )


def _replace_v1_url_proxies(
    proxy_type: Literal["stored_proxy", "explicit_proxy"],
    proxy_spec: str,
    global_proxies_with_lookup: GlobalProxiesWithLookup,
    usage_hint: str,
) -> ReplacementResult[v1.EnvProxy | v1.URLProxy]:
    if proxy_type == "explicit_proxy":
        return ReplacementResult(v1.URLProxy(url=proxy_spec), {}, {})

    try:
        global_proxy = global_proxies_with_lookup.global_proxies[proxy_spec]
    except KeyError:
        config_warnings.warn(f'The global proxy "{proxy_spec}" ({usage_hint}) does not exist.')
        return ReplacementResult(v1.EnvProxy(), {}, {})

    return ReplacementResult(
        v1.URLProxy(url=global_proxy.url(global_proxies_with_lookup.password_lookup, usage_hint)),
        {},
        {},
    )


def _replace_alpha_url_proxies(
    proxy_type: Literal["stored_proxy", "explicit_proxy"],
    proxy_spec: str,
    global_proxies_with_lookup: GlobalProxiesWithLookup,
    usage_hint: str,
) -> ReplacementResult[internal.EnvProxy | internal.URLProxy]:
    if proxy_type == "explicit_proxy":
        return ReplacementResult(internal.URLProxy(url=proxy_spec), {}, {})

    try:
        global_proxy = global_proxies_with_lookup.global_proxies[proxy_spec]
    except KeyError:
        config_warnings.warn(f'The global proxy "{proxy_spec}" ({usage_hint}) does not exist.')
        return ReplacementResult(internal.EnvProxy(), {}, {})

    return ReplacementResult(
        internal.URLProxy(
            url=global_proxy.url(global_proxies_with_lookup.password_lookup, usage_hint)
        ),
        {},
        {},
    )
