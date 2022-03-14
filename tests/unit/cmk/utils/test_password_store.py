#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.paths
from cmk.utils import password_store
from cmk.utils.config_path import LATEST_CONFIG
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.password_store import PasswordId

PW_STORE = "pw_from_store"
PW_EXPL = "pw_explicit"
PW_STORE_KEY = "from_store"


def test_save() -> None:
    assert password_store.load() == {}
    password_store.save({"ding": "blablu"})
    assert password_store.load()["ding"] == "blablu"


def test_save_for_helpers_no_store() -> None:
    assert not password_store.password_store_path().exists()

    assert password_store.load_for_helpers() == {}
    password_store.save_for_helpers(LATEST_CONFIG)

    assert not password_store.password_store_path().exists()
    assert not password_store._helper_password_store_path(LATEST_CONFIG).exists()
    assert password_store.load_for_helpers() == {}


def test_save_for_helpers() -> None:
    assert not password_store.password_store_path().exists()
    password_store.save({"ding": "blablu"})
    assert password_store.password_store_path().exists()
    assert password_store.load_for_helpers() == {}

    password_store.save_for_helpers(LATEST_CONFIG)
    assert password_store.load_for_helpers() == {"ding": "blablu"}


def load_patch() -> dict[str, str]:
    return {PW_STORE_KEY: PW_STORE}


@pytest.mark.parametrize(
    "password_id, password_actual",
    [
        (("password", PW_EXPL), PW_EXPL),
        (("store", PW_STORE_KEY), PW_STORE),
        (PW_STORE_KEY, PW_STORE),
    ],
)
def test_extract(
    monkeypatch: pytest.MonkeyPatch,
    password_id: PasswordId,
    password_actual: str,
) -> None:
    monkeypatch.setattr(password_store, "load", load_patch)
    assert password_store.extract(password_id) == password_actual


def test_extract_from_unknown_valuespec() -> None:
    password_id = ("unknown", "unknown_pw")
    with pytest.raises(MKGeneralException) as excinfo:
        # We test for an invalid structure here
        password_store.extract(password_id)  # type: ignore[arg-type]
    assert "Unknown password type." in str(excinfo.value)


def test_obfuscation() -> None:
    obfuscated = password_store._obfuscate(secret := "$ecret")
    assert (
        int.from_bytes(
            obfuscated[: password_store.PasswordStore.VERSION_BYTE_LENGTH],
            byteorder="big",
        )
        == password_store.PasswordStore.VERSION
    )
    assert password_store._deobfuscate(obfuscated) == secret


def test_save_obfuscated() -> None:
    password_store.save(data := {"ding": "blablu"})
    assert password_store.load() == data


def test_obfuscate_with_own_secret() -> None:
    obfuscated = password_store._obfuscate(secret := "$ecret")
    assert password_store._deobfuscate(obfuscated) == secret

    # The user may want to write some arbritary secret to the file.
    key_path = password_store.PasswordStore._secret_key_path()
    key_path.write_text(custom_key := "this_will_be_pretty_secure_now.not.")

    # Ensure we work with the right key file along the way
    assert (cmk.utils.paths.omd_root / "etc" / "password_store.secret").read_text() == custom_key

    # Old should not be decryptable anymore
    with pytest.raises(ValueError, match="MAC check failed"):
        assert password_store._deobfuscate(obfuscated)

    # Test encryption and decryption with new key
    assert password_store._deobfuscate(password_store._obfuscate(secret)) == secret


def test_encrypt_decrypt_identity() -> None:
    data = "some random data to be encrypted"
    assert password_store.PasswordStore.decrypt(password_store.PasswordStore.encrypt(data)) == data
