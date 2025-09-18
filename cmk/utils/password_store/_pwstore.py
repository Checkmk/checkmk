#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Literal, NotRequired, TypedDict
from uuid import uuid4

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.exceptions import MKGeneralException
from cmk.crypto.symmetric import aes_gcm_decrypt, aes_gcm_encrypt, TaggedCiphertext
from cmk.utils.global_ident_type import GlobalIdent
from cmk.utils.local_secrets import PasswordStoreSecret

PasswordLookupType = Literal["password", "store"]
PasswordId = str | tuple[PasswordLookupType, str]


# CMK-16660
# _PASSWORD_ID_PREFIX = ":uuid:"  # cannot collide with user defined id.
_PASSWORD_ID_PREFIX = "uuid"


class Password(TypedDict):
    title: str
    comment: str
    docu_url: str
    password: str
    # Only owners can edit the password
    # None -> Administrators (having the permission "Write access to all passwords")
    # str -> Name of the contact group owning the password
    owned_by: str | None
    shared_with: list[str]
    customer: NotRequired[str | None]
    locked_by: NotRequired[GlobalIdent]


def password_store_path() -> Path:
    """file where the user-managed passwords are stored."""
    return cmk.utils.paths.var_dir / "stored_passwords"


def core_password_store_path(config_path: Path | None = None) -> Path:
    """file where the passwords for use by the helpers are stored

    This is "frozen" in the state at config generation.
    """
    if config_path is None:
        # TODO: Make non-optional
        config_path = VersionedConfigPath.make_latest_path(cmk.utils.paths.omd_root)
    return config_path / "stored_passwords"


def pending_password_store_path() -> Path:
    """file where user-managed passwords and the ones extracted from the configuration are merged."""
    return cmk.utils.paths.var_dir / "passwords_merged"


def save(passwords: Mapping[str, str], store_path: Path) -> None:
    """Save the passwords to the pre-activation path"""
    store_path.parent.mkdir(parents=True, exist_ok=True)
    content = ""
    for ident, pw in passwords.items():
        # This is normally needed to not break the file format for things like gcp tokens.
        # The GUI does this automatically by having only one line of input field,
        # but other sources (like the REST API) use this function as well.
        password_on_one_line = pw.replace("\n", "")
        content += f"{ident}:{password_on_one_line}\n"

    store.save_bytes_to_file(store_path, PasswordStore.encrypt(content))


def load(store_path: Path) -> dict[str, str]:
    with suppress(FileNotFoundError):
        store_path_bytes: bytes = store_path.read_bytes()
        if not store_path_bytes:
            return {}
        return _deserialise_passwords(PasswordStore.decrypt(store_path_bytes))
    return {}


def _deserialise_passwords(raw: str) -> dict[str, str]:
    """
    This is designed to work with a _PASSWORD_ID_PREFIX that
    contains a colon at the beginning and the end, but
    that is not supported by the other implementations.

    >>> _deserialise_passwords("my_stored:p4ssw0rd\\nuuid1234:s3:cr37!")
    {'my_stored': 'p4ssw0rd', 'uuid1234': 's3:cr37!'}

    """
    passwords: dict[str, str] = {}
    for line in raw.splitlines():
        if (sline := line.strip()).startswith(_PASSWORD_ID_PREFIX):
            uuid, password = sline.removeprefix(_PASSWORD_ID_PREFIX).split(":", 1)
            ident = f"{_PASSWORD_ID_PREFIX}{uuid}"
        else:
            ident, password = sline.split(":", 1)
        passwords[ident] = password

    return passwords


def ad_hoc_password_id() -> str:
    return f"{_PASSWORD_ID_PREFIX}{uuid4()}"


def extract_formspec_password(
    password: tuple[Literal["cmk_postprocessed"], Literal["stored_password"], tuple[str, str]]
    | tuple[Literal["cmk_postprocessed"], Literal["explicit_password"], tuple[str, str]],
) -> str:
    match password:
        case ("cmk_postprocessed", "explicit_password", (password_id, password_value)):
            # This is a password that was entered in the GUI, so we can return it directly.
            return password_value
        case ("cmk_postprocessed", "stored_password", (password_id, str())):
            if (pw := load(pending_password_store_path()).get(password_id)) is None:
                raise MKGeneralException(
                    "Password not found in pending password store. Please check the password store."
                )
            return pw
        case _:
            raise MKGeneralException(
                f"Unknown password type {password}. Expected 'cmk_postprocessed'."
            )


def extract(password_id: PasswordId) -> str:
    """Translate the password store reference to the actual password. This function is likely
    to be used by third party plugins and should not be moved / changed in behaviour."""
    staging_path = pending_password_store_path()
    match password_id:
        case str():
            if (pw := load(staging_path).get(password_id)) is None:
                raise MKGeneralException(
                    f"Password not found in '{staging_path}'. Please check the password store."
                )
            return pw
        # In case we get a tuple, assume it was coming from a ValueSpec "IndividualOrStoredPassword"
        case ("password", pw):
            return pw
        case ("store", pw_id):
            if (pw := load(staging_path).get(pw_id)) is None:
                raise MKGeneralException(
                    f"Password not found in '{staging_path}'. Please check the password store."
                )
            return pw
        case _:
            raise MKGeneralException("Unknown password type.")


def make_staged_passwords_lookup() -> Callable[[str], str | None]:
    """Returns something similar to `extract`. Intended for internal use only."""
    staging_path = (
        pending_password_store_path()
    )  # maybe we should pass this, but lets be consistent for now.
    store = load(staging_path)
    return store.get


def lookup(pw_file: Path, pw_id: str) -> str:
    """Look up the password with id <id> in the file <file> and return it.

    Raises:
        ValueError: If the password_id is not found in the password store.

    Returns:
        The password as found in the password store.
    """
    try:
        return load(pw_file)[pw_id]
    except KeyError:
        # the fact that this is a dict is an implementation detail.
        # Let's make it a ValueError.
        raise ValueError(f"Password '{pw_id}' not found in {pw_file}")


def lookup_for_bakery(pw_id: str) -> str:
    return lookup(core_password_store_path(), pw_id)


class PasswordStore:
    VERSION = 0
    VERSION_BYTE_LENGTH = 2

    SALT_LENGTH: int = 16
    NONCE_LENGTH: int = 16

    @staticmethod
    def encrypt(value: str) -> bytes:
        salt = os.urandom(PasswordStore.SALT_LENGTH)
        nonce = os.urandom(PasswordStore.NONCE_LENGTH)
        key = PasswordStoreSecret().derive_secret_key(salt)
        encrypted = aes_gcm_encrypt(key, nonce, value)
        return (
            PasswordStore.VERSION.to_bytes(PasswordStore.VERSION_BYTE_LENGTH, byteorder="big")
            + salt
            + nonce
            + encrypted.tag
            + encrypted.ciphertext
        )

    @staticmethod
    def decrypt(raw: bytes) -> str:
        _version, rest = (
            raw[: PasswordStore.VERSION_BYTE_LENGTH],
            raw[PasswordStore.VERSION_BYTE_LENGTH :],
        )
        salt, rest = rest[: PasswordStore.SALT_LENGTH], rest[PasswordStore.SALT_LENGTH :]
        nonce, rest = rest[: PasswordStore.NONCE_LENGTH], rest[PasswordStore.NONCE_LENGTH :]
        tag, encrypted = rest[: TaggedCiphertext.TAG_LENGTH], rest[TaggedCiphertext.TAG_LENGTH :]
        key = PasswordStoreSecret().derive_secret_key(salt)
        return aes_gcm_decrypt(key, nonce, TaggedCiphertext(ciphertext=encrypted, tag=tag))
