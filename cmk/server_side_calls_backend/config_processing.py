#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, Literal, Self, TypeVar

from cmk.server_side_calls.v1 import EnvProxy, NoProxy, Secret, URLProxy
from cmk.utils import config_warnings

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


@dataclass(frozen=True, kw_only=True)
class PreprocessingResult:
    processed_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]]
    ad_hoc_secrets: Mapping[str, str]

    @classmethod
    def from_config(
        cls, rules_by_name: Sequence[tuple[str, Sequence[Mapping[str, object]]]]
    ) -> Self:
        """
        >>> PreprocessingResult.from_config(
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
        PreprocessingResult(processed_rules=[('pure_storage_fa', [{'api_token': Secret(...), 'timeout': 5.0}])], ad_hoc_secrets={':uuid:1234': 'knubblwubbl'})
        """
        preprocessing_results = [
            (name, [process_configuration_to_parameters(rule) for rule in rules])
            for name, rules in rules_by_name
        ]

        return cls(
            processed_rules=[
                (name, [res.value for res in prep]) for name, prep in preprocessing_results
            ],
            ad_hoc_secrets={
                k: v
                for name, prep in preprocessing_results
                for res in prep
                for k, v in res.found_secrets.items()
            },
        )


_RuleSetType_co = TypeVar("_RuleSetType_co", covariant=True)


@dataclass(frozen=True)
class ProxyConfig:
    host_name: str
    global_proxies: Mapping[str, Mapping[str, str]]


@dataclass(frozen=True)
class ReplacementResult(Generic[_RuleSetType_co]):
    value: _RuleSetType_co
    found_secrets: Mapping[str, str]
    surrogates: Mapping[int, str]


def process_configuration_to_parameters(
    params: Mapping[str, object],
    proxy_config: ProxyConfig | None = None,
) -> ReplacementResult[Mapping[str, object]]:
    d_results = [(k, _processed_config_value(v, proxy_config)) for k, v in params.items()]
    return ReplacementResult(
        value={k: res.value for k, res in d_results},
        found_secrets={k: v for _, res in d_results for k, v in res.found_secrets.items()},
        surrogates={k: v for _, res in d_results for k, v in res.surrogates.items()},
    )


def _processed_config_value(
    params: object,
    proxy_config: ProxyConfig | None,
) -> ReplacementResult[object]:
    match params:
        case list():
            results = [_processed_config_value(v, proxy_config) for v in params]
            return ReplacementResult(
                value=[res.value for res in results],
                found_secrets={k: v for res in results for k, v in res.found_secrets.items()},
                surrogates={k: v for res in results for k, v in res.surrogates.items()},
            )
        case tuple():
            match params:
                case ("cmk_postprocessed", "stored_password", value):
                    return _replace_password(value[0], None)
                case ("cmk_postprocessed", "explicit_password", value):
                    return _replace_password(*value)
                case (
                    "cmk_postprocessed",
                    "stored_proxy" | "environment_proxy" | "explicit_proxy" | "no_proxy",
                    str(),
                ):
                    if proxy_config is not None:
                        return ReplacementResult(
                            value=_replace_proxies(params, proxy_config),
                            found_secrets={},
                            surrogates={},
                        )

            results = [_processed_config_value(v, proxy_config) for v in params]
            return ReplacementResult(
                value=tuple(res.value for res in results),
                found_secrets={k: v for res in results for k, v in res.found_secrets.items()},
                surrogates={k: v for res in results for k, v in res.surrogates.items()},
            )
        case dict():
            return process_configuration_to_parameters(params, proxy_config)
    return ReplacementResult(value=params, found_secrets={}, surrogates={})


def _replace_password(
    name: str,
    value: str | None,
) -> ReplacementResult:
    # We need some injective function.
    surrogate = id(name)
    return ReplacementResult(
        value=Secret(surrogate),
        found_secrets={} if value is None else {name: value},
        surrogates={surrogate: name},
    )


def _replace_proxies(
    proxy_params: tuple[
        Literal["cmk_postprocessed"],
        Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
        str,
    ],
    proxy_config: ProxyConfig,
) -> URLProxy | NoProxy | EnvProxy:
    match proxy_params:
        case ("cmk_postprocessed", "stored_proxy", str(proxy_id)):
            try:
                global_proxy = proxy_config.global_proxies[proxy_id]
                return URLProxy(url=global_proxy["proxy_url"])
            except KeyError:
                config_warnings.warn(
                    f'The global proxy "{proxy_id}" used by host "{proxy_config.host_name}"'
                    " does not exist."
                )
                return EnvProxy()
        case ("cmk_postprocessed", "environment_proxy", str()):
            return EnvProxy()
        case ("cmk_postprocessed", "explicit_proxy", str(url)):
            return URLProxy(url=url)
        case ("cmk_postprocessed", "no_proxy", str()):
            return NoProxy()
        case _:
            raise ValueError(f"Invalid proxy configuration: {proxy_config}")
