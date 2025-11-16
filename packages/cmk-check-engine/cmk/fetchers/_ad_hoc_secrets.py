#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.store import save_bytes_to_file
from cmk.password_store.v1_unstable import get_store_secret, PasswordStore, Secret

__all__ = [
    "AdHocSecrets",
    "ad_hoc_secrets_file",
]


@dataclass(frozen=True)
class AdHocSecrets:
    path: Path
    secrets: Mapping[str, Secret[str]]


@contextmanager
def ad_hoc_secrets_file(
    ad_hoc_secrets: AdHocSecrets,
) -> Iterator[None]:
    """Create a temporary password store file for the given passwords.
    The file is created at the given path and deleted when the context is exited.
    """
    ad_hoc_secrets.path.parent.mkdir(parents=True, exist_ok=True)
    save_bytes_to_file(
        ad_hoc_secrets.path, PasswordStore(get_store_secret()).dump_bytes(ad_hoc_secrets.secrets)
    )
    try:
        yield
    finally:
        ad_hoc_secrets.path.unlink(missing_ok=True)
