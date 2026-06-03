#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import binascii
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

import cmk.utils.paths
from cmk.utils import password_store
from cmk.utils.crypto.secrets import PasswordStoreSecret
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.password_store import PasswordId, PasswordStore

PW_STORE = "pw_from_store"
PW_EXPL = "pw_explicit"
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


def load_patch(_file_path: Path) -> dict[str, str]:
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
    obfuscated = PasswordStore.encrypt(secret := "$ecret")
    assert (
        int.from_bytes(
            obfuscated[: PasswordStore.VERSION_BYTE_LENGTH],
            byteorder="big",
        )
        == PasswordStore.VERSION
    )
    assert PasswordStore.decrypt(obfuscated) == secret


def test_obfuscate_with_own_secret() -> None:
    obfuscated = PasswordStore.encrypt(secret := "$ecret")
    assert PasswordStore.decrypt(obfuscated) == secret

    # The user may want to write some arbritary secret to the file.
    cmk.utils.paths.password_store_secret_file.write_bytes(b"this_will_be_pretty_secure_now.not.")

    # Old should not be decryptable anymore
    with pytest.raises(InvalidTag):
        assert PasswordStore.decrypt(obfuscated)

    # Test encryption and decryption with new key
    assert PasswordStore.decrypt(PasswordStore.encrypt(secret)) == secret


def test_encrypt_decrypt_identity() -> None:
    data = "some random data to be encrypted"
    assert PasswordStore.decrypt(PasswordStore.encrypt(data)) == data


def _explicit(uuid: str, value: str) -> tuple:
    return ("cmk_postprocessed", "explicit_password", (uuid, value))


def _stored(pw_id: str) -> tuple:
    return ("cmk_postprocessed", "stored_password", (pw_id, ""))


def test_preserve_uuids_top_level_unchanged_password() -> None:
    old = _explicit("uuid-old", "s3cr3t")
    new = _explicit("uuid-new", "s3cr3t")
    assert password_store.preserve_explicit_password_uuids(new, old) == _explicit(
        "uuid-old", "s3cr3t"
    )


def test_preserve_uuids_top_level_changed_password() -> None:
    """UUID is a slot identifier, not derived from the value: preserve even on value change."""
    old = _explicit("uuid-old", "s3cr3t")
    new = _explicit("uuid-new", "new-s3cr3t")
    assert password_store.preserve_explicit_password_uuids(new, old) == _explicit(
        "uuid-old", "new-s3cr3t"
    )


def test_preserve_uuids_no_orig_counterpart() -> None:
    new = _explicit("uuid-new", "s3cr3t")
    assert password_store.preserve_explicit_password_uuids(new, None) == new
    assert password_store.preserve_explicit_password_uuids(new, "some scalar") == new


def test_preserve_uuids_throwaway_sentinel() -> None:
    """The migration sentinel emitted by migrate_to_password must not be propagated."""
    old = _explicit("throwaway-id", "s3cr3t")
    new = _explicit("uuid-new", "s3cr3t")
    assert password_store.preserve_explicit_password_uuids(new, old) == new


def test_preserve_uuids_invalid_old_uuid() -> None:
    new = _explicit("uuid-new", "s3cr3t")
    assert password_store.preserve_explicit_password_uuids(new, _explicit("", "s3cr3t")) == new
    assert (
        password_store.preserve_explicit_password_uuids(
            new, ("cmk_postprocessed", "explicit_password", (None, "s3cr3t"))
        )
        == new
    )


def test_preserve_uuids_stored_password_passthrough() -> None:
    """Stored-password triples use user-chosen IDs and must not be rewritten."""
    new = _stored("my_db_password")
    old = _stored("my_db_password")
    assert password_store.preserve_explicit_password_uuids(new, old) == new


def test_preserve_uuids_buried_inside_dict_and_list() -> None:
    old = {"creds": [{"primary": _explicit("uuid-old", "s3cr3t")}]}
    new = {"creds": [{"primary": _explicit("uuid-new", "s3cr3t")}]}
    assert password_store.preserve_explicit_password_uuids(new, old) == {
        "creds": [{"primary": _explicit("uuid-old", "s3cr3t")}]
    }


def test_preserve_uuids_two_passwords_independent() -> None:
    old = {
        "a": _explicit("uuid-a-old", "p1"),
        "b": _explicit("uuid-b-old", "p2"),
    }
    new = {
        "a": _explicit("uuid-a-new", "p1-changed"),
        "b": _explicit("uuid-b-new", "p2"),
    }
    result = password_store.preserve_explicit_password_uuids(new, old)
    assert result == {
        "a": _explicit("uuid-a-old", "p1-changed"),
        "b": _explicit("uuid-b-old", "p2"),
    }


def test_preserve_uuids_dict_key_added_in_new() -> None:
    old = {"a": _explicit("uuid-a-old", "p1")}
    new = {
        "a": _explicit("uuid-a-new", "p1"),
        "b": _explicit("uuid-b-new", "p2"),
    }
    result = password_store.preserve_explicit_password_uuids(new, old)
    assert result == {
        "a": _explicit("uuid-a-old", "p1"),
        "b": _explicit("uuid-b-new", "p2"),
    }


def test_preserve_uuids_list_length_mismatch_passes_new_through() -> None:
    old = [_explicit("uuid-old", "s3cr3t")]
    new = [
        _explicit("uuid-new-0", "s3cr3t"),
        _explicit("uuid-new-1", "other"),
    ]
    assert password_store.preserve_explicit_password_uuids(new, old) == new


def test_preserve_uuids_scalars_and_none() -> None:
    assert password_store.preserve_explicit_password_uuids("x", "y") == "x"
    assert password_store.preserve_explicit_password_uuids(None, None) is None
    assert password_store.preserve_explicit_password_uuids(42, "str") == 42


@pytest.mark.usefixtures("fixed_secret")
def test_pw_store_characterization() -> None:
    """This is a characterization (aka "golden master") test to ensure that the password store can
    still decrypt passwords it encrypted before.

    This can only work if the local secret is fixed of course, but a change in the container format,
    the key generation, or algorithms used would be detected.
    """
    # generated by PasswordStore._obfuscate as of commit 79900beda42310dfea9f5bd704041f4e10936ba8
    encrypted = binascii.unhexlify(
        b"00003b1cedb92526621483f9ba140fbe"
        b"55f49916ae77a11a2ac93b4db0758061"
        b"71a62a8aedd3d1edd67e558385a98efe"
        b"be3c4c0ca364e54ff6ad2fa7ef48a0e8"
        b"8ed989283e9604e07da89301658f0370"
        b"d35bba1a8abf74bc971975"
    )

    assert PasswordStore.decrypt(encrypted) == "Time is an illusion. Lunchtime doubly so."
