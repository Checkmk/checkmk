#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Iterable, Literal, Self

from cmk.server_side_calls.v1 import Secret

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


@dataclass(frozen=True, kw_only=True)
class PreprocessingResult:
    processed_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]]
    ad_hoc_secrets: Mapping[str, str]

    @classmethod
    def from_config(
        cls, rules_by_name: Sequence[tuple[str, Sequence[Mapping[str, object]]]]
    ) -> Self:
        preprocessing_results = (
            (name, [process_configuration_into_parameters(rule) for rule in rules])
            for name, rules in rules_by_name
        )

        return cls(
            processed_rules=[
                (name, [rule for rule, _found_secrets in prep])
                for name, prep in preprocessing_results
            ],
            ad_hoc_secrets={
                # TODO: add ad hoc secrets here as soon as we have an id for them
            },
        )


_ConfiguredPassword = tuple[Literal["store", "password"], str]


def process_configuration_into_parameters(
    params: Mapping[str, object]
) -> tuple[Mapping[str, object | Secret], Mapping[int, _ConfiguredPassword]]:
    # Note: we really replace either the value, or some part of the value, with a Secret.
    # We can't type this with a TypeVar.
    # TODO: clean this up to not use a mutable argument
    found_secrets: dict[int, _ConfiguredPassword] = {}
    return {k: _processed_config_value(v, found_secrets) for k, v in params.items()}, found_secrets


def _processed_config_value(
    params: object, found_secrets: MutableMapping[int, _ConfiguredPassword]
) -> object | Secret:
    match params:
        case list():
            return [_processed_config_value(v, found_secrets) for v in params]
        case tuple():
            match params:
                case ("password" | "store", str()) as passwd_config:
                    return _replace_password(passwd_config, found_secrets)
            return tuple(_processed_config_value(v, found_secrets) for v in params)
        case dict():
            return {k: _processed_config_value(v, found_secrets) for k, v in params.items()}
    return params


def _replace_password(
    passwd_config: tuple[Literal["store", "password"], str],
    found_secrets: MutableMapping[int, tuple[Literal["store", "password"], str]],
) -> Secret:
    secret = Secret(hash(passwd_config))
    found_secrets[secret.id] = passwd_config
    return secret
