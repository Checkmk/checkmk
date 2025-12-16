#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shlex
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Protocol

from cmk.discover_plugins import discover_executable, family_libexec_dir
from cmk.password_store.v1_unstable import get_store_secret, PasswordStore
from cmk.password_store.v1_unstable import Secret as StoreSecret
from cmk.server_side_calls.v1 import Secret
from cmk.utils import config_warnings, password_store

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


ConfigSet = Mapping[str, object]
SSCRules = tuple[str, Sequence[ConfigSet]]


def load_secrets_file(path: Path) -> Mapping[str, StoreSecret[str]]:
    try:
        store_path_bytes = path.read_bytes()
    except FileNotFoundError:
        return {}

    return (
        PasswordStore(get_store_secret()).load_bytes(store_path_bytes) if store_path_bytes else {}
    )


class SecretsConfig(Protocol):
    @property
    def secrets(self) -> Mapping[str, StoreSecret[str]]:
        """The secrets (by ID) that the SSC can expect to be in the file."""
        ...

    @property
    def path(self) -> Path:
        """The path that should be baked into the command line.
        This is where the SSC will look for the secrets.
        """
        ...


def replace_passwords(
    host_name: str,
    arguments: Sequence[str | Secret],
    secrets_config: SecretsConfig,
    surrogated_secrets: Mapping[int, str],
    *,
    apply_password_store_hack: bool,
) -> tuple[str, ...]:
    formatted: list[str | tuple[str, str, str]] = []

    for index, arg in enumerate(arguments):
        if isinstance(arg, str):
            formatted.append(shlex.quote(arg))
            continue

        if not isinstance(arg, Secret):
            # this can only happen if plugin developers are ignoring the API's typing.
            raise _make_helpful_exception(index, arguments)

        secret = arg
        secret_name = surrogated_secrets[secret.id]

        if secret.pass_safely:
            formatted.append(shlex.quote(f"{secret_name}:{secrets_config.path}"))
            continue

        # we are meant to pass it as plain secret here, but we
        # maintain a list of plugins that have a very special hack in place.

        if apply_password_store_hack:
            # fall back to old hack, for now
            formatted.append(("store", secret_name, arg.format))
            continue

        # TODO: I think we can check this much earlier now.
        try:
            secret_value = secrets_config.secrets[secret_name].reveal()
        except KeyError:
            config_warnings.warn(
                f'The stored password "{secret_name}" used by host "{host_name}" does not exist.'
            )
            secret_value = "%%%"
        formatted.append(shlex.quote(secret.format % secret_value))

    return tuple(
        password_store.hack.apply_password_hack(
            formatted,
            secrets_config.secrets,
            secrets_config.path,
            config_warnings.warn,
            _make_log_label(host_name),
        ),
    )


def _make_log_label(host_name: str) -> str:
    return f' used by host "{host_name}"'


def _make_helpful_exception(index: int, arguments: Sequence[str | Secret]) -> TypeError:
    """Create a developer-friendly exception for invalid arguments"""
    raise TypeError(
        f"Got invalid argument list from SSC plugin: {arguments[index]!r} at index {index} in {arguments!r}. "
        "Expected either `str` or `Secret`."
    )


class ExecutableFinderProtocol(Protocol):
    def __call__(self, executable: str, module: str | None) -> str: ...


class ExecutableFinder:
    def __init__(
        self,
        local_search_path: Path,
        shipped_search_path: Path,
        *,
        prefix_map: Sequence[tuple[Path, Path]],
    ) -> None:
        self._additional_search_paths = (local_search_path, shipped_search_path)
        self._prefix_map = prefix_map

    def _stripped(self, path: Path) -> str:
        for prefix, replacement in self._prefix_map:
            if path.is_relative_to(prefix):
                return str(replacement / path.relative_to(prefix))
        return str(path)

    def __call__(self, executable: str, module: str | None) -> str:
        libexec_paths = () if module is None else (family_libexec_dir(module),)
        full_path = discover_executable(executable, *libexec_paths, *self._additional_search_paths)
        return self._stripped(full_path) if full_path else executable
