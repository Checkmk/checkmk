#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.password_store.v1_alpha import Secret
from cmk.utils import password_store
from cmk.utils.local_secrets import PasswordStoreSecret
from cmk.utils.password_store import PasswordId

PW_STORE = Secret("pw_from_store")
PW_EXPL = Secret("pw_explicit")
PW_STORE_KEY = "from_store"


@pytest.fixture(name="fixed_secret")
def fixture_fixed_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Write a fixed value to a tmp file and use that file for the password store secret

    we need the old value since other tests rely on the general path mocking"""
    secret = b"password-secret"
    secret_path = tmp_path / "password_store_fixed.secret"
    secret_path.write_bytes(secret)
    monkeypatch.setattr(PasswordStoreSecret, "path", secret_path)


def test_save(tmp_path: Path) -> None:
    file = tmp_path / "password_store"
    assert not password_store.load(file)
    password_store.save(data := {"ding": "blablu"}, file)
    assert password_store.load(file) == data


def load_patch(_file_path: Path) -> Mapping[str, Secret[str]]:
    return {PW_STORE_KEY: PW_STORE}


@pytest.mark.parametrize(
    "password_id, password_actual",
    [
        (("password", PW_EXPL.reveal()), PW_EXPL),
        (("store", PW_STORE_KEY), PW_STORE),
        (PW_STORE_KEY, PW_STORE),
    ],
)
def test_extract(
    monkeypatch: pytest.MonkeyPatch,
    password_id: PasswordId,
    password_actual: Secret[str],
) -> None:
    monkeypatch.setattr(password_store._pwstore, "_load", load_patch)
    assert password_store.extract(password_id) == password_actual.reveal()


def test_extract_from_unknown_valuespec() -> None:
    password_id = ("unknown", "unknown_pw")
    with pytest.raises(MKGeneralException) as excinfo:
        # We test for an invalid structure here
        password_store.extract(password_id)  # type: ignore[arg-type]
    assert "Unknown password type." in str(excinfo.value)
