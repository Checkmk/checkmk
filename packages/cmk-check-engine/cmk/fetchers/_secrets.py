#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from cmk.ccc.store import save_bytes_to_file
from cmk.password_store.v1_unstable import get_store_secret, PasswordStore, Secret

__all__ = [
    "FetcherSecrets",
    "StoredSecrets",
    "AdHocSecrets",
]


@dataclass(frozen=True)
class StoredSecrets:
    """Use these secrets, but assume the file is already present on disk."""

    path: Path
    secrets: Mapping[str, Secret[str]]

    @property
    def provide_file(self) -> type[AbstractContextManager[None]]:
        return nullcontext


@dataclass(frozen=True)
class ActivatedSecrets:
    """Use the currently activated secrets

    This is intended for use in the fetcher controller, where we don't need to
    know the actual secrets.
    """

    @property
    def provide_file(self) -> type[AbstractContextManager[None]]:
        return nullcontext


@dataclass(frozen=True)
class AdHocSecrets:
    """Use these secrets, and make them available via a temporary file."""

    path: Path
    secrets: Mapping[str, Secret[str]]

    def serialize(self) -> Mapping[str, str | Mapping[str, str]]:
        return {
            "path": str(self.path),
            "secrets": {k: s.reveal() for k, s in self.secrets.items()},
        }

    @classmethod
    def deserialize(cls, data: Mapping[str, object]) -> Self:
        match data:
            case {"path": str() as path, "secrets": {**secrets}}:
                return cls(
                    path=Path(path),
                    secrets={str(k): Secret(str(v)) for k, v in secrets.items()},
                )
            case _:
                # don't include the data in the error message, it might contain secrets
                raise ValueError("Invalid data for AdHocSecrets deserialization")

    @contextmanager
    def provide_file(self) -> Iterator[None]:
        """Create a temporary password store file for the given passwords.
        The file is created at the given path and deleted when the context is exited.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        save_bytes_to_file(self.path, PasswordStore(get_store_secret()).dump_bytes(self.secrets))
        try:
            yield
        finally:
            self.path.unlink(missing_ok=True)


type FetcherSecrets = AdHocSecrets | StoredSecrets | ActivatedSecrets
