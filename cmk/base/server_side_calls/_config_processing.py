#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from typing import Iterable, Literal

from cmk.server_side_calls.v1 import Secret

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


_ConfiguredPassword = tuple[Literal["store", "password"], str]


def process_configuration_into_parameters(
    params: Mapping[str, object]
) -> tuple[Mapping[str, object | Secret], Mapping[int, _ConfiguredPassword]]:
    # Note: we really replace either the value, or some part of the value, with a Secret.
    # We can't type this with a TypeVar.
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
