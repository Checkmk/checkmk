#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from cmk.server_side_calls import alpha, v1
from cmk.utils import config_warnings

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


@dataclass(frozen=True)
class ProxyConfig:
    url: str
    # TODO: add auth here.


type GlobalProxies = Mapping[str, ProxyConfig]


def extract_all_adhoc_secrets(
    rules_by_name: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    # TODO: we will have to pass proxy config here as well if global proxies can contain explicit secrets
    global_proxies: GlobalProxies = {},  # TODO
) -> Mapping[str, str]:
    """
    >>> extract_all_adhoc_secrets(
    ...     [
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
    ... )
    {':uuid:1234': 'knubblwubbl'}
    """
    use_alpha = True  # whatever is more comprehensive in extracting secrets
    preprocessing_results = [
        (
            name,
            [
                process_configuration_to_parameters(
                    rule, global_proxies, f"ruleset: {name}", use_alpha
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
    global_proxies: GlobalProxies,
    usage_hint: str,
    is_alpha: bool,
) -> ReplacementResult[Mapping[str, object]]:
    d_results = [
        (k, _processed_config_value(v, global_proxies, usage_hint, is_alpha))
        for k, v in params.items()
    ]
    return ReplacementResult(
        value={k: res.value for k, res in d_results},
        found_secrets={k: v for _, res in d_results for k, v in res.found_secrets.items()},
        surrogates={k: v for _, res in d_results for k, v in res.surrogates.items()},
    )


def _processed_config_value(
    params: object,
    global_proxies: GlobalProxies,
    usage_hint: str,
    is_alpha: bool,
) -> ReplacementResult[object]:
    match params:
        case list():
            results = [
                _processed_config_value(v, global_proxies, usage_hint, is_alpha) for v in params
            ]
            return ReplacementResult(
                value=[res.value for res in results],
                found_secrets={k: v for res in results for k, v in res.found_secrets.items()},
                surrogates={k: v for res in results for k, v in res.surrogates.items()},
            )
        case tuple():
            match params:
                case ("cmk_postprocessed", "stored_password", value):
                    return _replace_password(value[0], None, is_alpha=is_alpha)
                case ("cmk_postprocessed", "explicit_password", value):
                    return _replace_password(value[0], value[1], is_alpha=is_alpha)
                case ("cmk_postprocessed", "no_proxy", str()):
                    return ReplacementResult(alpha.NoProxy() if is_alpha else v1.NoProxy(), {}, {})
                case ("cmk_postprocessed", "environment_proxy", str()):
                    return ReplacementResult(
                        alpha.EnvProxy() if is_alpha else v1.EnvProxy(), {}, {}
                    )
                case (
                    "cmk_postprocessed",
                    "stored_proxy" | "explicit_proxy" as proxy_type,
                    str(proxy_spec),
                ):
                    return (
                        _replace_alpha_url_proxies(
                            proxy_type, proxy_spec, global_proxies, usage_hint
                        )
                        if is_alpha
                        else _replace_v1_url_proxies(
                            proxy_type, proxy_spec, global_proxies, usage_hint
                        )
                    )

            results = [
                _processed_config_value(v, global_proxies, usage_hint, is_alpha) for v in params
            ]
            return ReplacementResult(
                value=tuple(res.value for res in results),
                found_secrets={k: v for res in results for k, v in res.found_secrets.items()},
                surrogates={k: v for res in results for k, v in res.surrogates.items()},
            )
        case dict():
            return process_configuration_to_parameters(params, global_proxies, usage_hint, is_alpha)
    return ReplacementResult(value=params, found_secrets={}, surrogates={})


def _replace_password(
    name: str,
    value: str | None,
    is_alpha: bool,
) -> ReplacementResult:
    # We need some injective function.
    surrogate = id(name)
    return ReplacementResult(
        value=(alpha.Secret if is_alpha else v1.Secret)(surrogate),
        found_secrets={} if value is None else {name: value},
        surrogates={surrogate: name},
    )


def _replace_v1_url_proxies(
    proxy_type: Literal["stored_proxy", "explicit_proxy"],
    proxy_spec: str,
    global_proxies: GlobalProxies,
    usage_hint: str,
) -> ReplacementResult[v1.EnvProxy | v1.URLProxy]:
    if proxy_type == "explicit_proxy":
        return ReplacementResult(v1.URLProxy(url=proxy_spec), {}, {})

    try:
        global_proxy = global_proxies[proxy_spec]
    except KeyError:
        config_warnings.warn(f'The global proxy "{proxy_spec}" ({usage_hint}) does not exist.')
        return ReplacementResult(v1.EnvProxy(), {}, {})

    return ReplacementResult(v1.URLProxy(url=global_proxy.url), {}, {})


def _replace_alpha_url_proxies(
    proxy_type: Literal["stored_proxy", "explicit_proxy"],
    proxy_spec: str,
    global_proxies: GlobalProxies,
    usage_hint: str,
) -> ReplacementResult[alpha.EnvProxy | alpha.URLProxy]:
    if proxy_type == "explicit_proxy":
        return ReplacementResult(alpha.URLProxy(url=proxy_spec), {}, {})

    try:
        global_proxy = global_proxies[proxy_spec]
    except KeyError:
        config_warnings.warn(f'The global proxy "{proxy_spec}" ({usage_hint}) does not exist.')
        return ReplacementResult(alpha.EnvProxy(), {}, {})

    return ReplacementResult(alpha.URLProxy(url=global_proxy.url), {}, {})
