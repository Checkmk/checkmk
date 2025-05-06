#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module is meant to be used by components (e.g. active checks, notifications, bakelets)
that support getting credentials from the Check_MK password store.

The password stores primary use is to centralize stored credentials. Instead of spreading the
credentials in the whole configuration, we have this as a central place for sensitive information.

The password store mechanic provides a mechanism for keeping passwords out of the cmdline of a
process, e.g. an active check plug-in. It has been built to extend existing plugins with as small
modificiations as possible. It is built out of two parts:

a) Adding arguments for the command line. This job is done for active checks plugins by
   `cmk.base.core_config._prepare_check_command` and `cmk.base.check_api.passwordstore_get_cmdline`.

b) Extracting arguments from the command line. This is done by `password_store.replace_passwords`
   for python plugins and for C monitoring plug-ins by the patches which can be found at
   `omd/packages/monitoring-plugins/patches/0003-cmk-password-store.dif`.

   The most interesting part is, that the password store arguments are replaced before the existing
   argument handling of the active check plug-ins is executed. This way we don't have to deal with
   the individual mechanics of the active check plug-ins. We can hook into the entry point of the
   plugin, do our work and leave the rest to the plugin.

Python active check plug-ins need to do something like this before the argv are processed.

  import cmk.utils.password_store
  cmk.utils.password_store.replace_passwords()

  (... use regular argv processing ...)

For cases where the password ID is not received from the command line, for example a configuration
file, there is the `extract` function which can be used like this:

  import cmk.utils.password_store
  password = cmk.utils.password_store.extract("pw_id")

"""

import os
import sys
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from typing import Literal
from uuid import uuid4

from typing_extensions import TypedDict

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.config_path import ConfigPath, LATEST_CONFIG
from cmk.utils.crypto.secrets import PasswordStoreSecret
from cmk.utils.crypto.symmetric import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    TaggedCiphertext,
)
from cmk.utils.exceptions import MKGeneralException

from . import hack

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


def password_store_path() -> Path:
    """file where the user-managed passwords are stored."""
    return Path(cmk.utils.paths.var_dir, "stored_passwords")


def core_password_store_path(config_path: ConfigPath) -> Path:
    """file where the passwords for use by the helpers are stored

    This is "frozen" in the state at config generation.
    """
    return Path(config_path) / "stored_passwords"


def pending_password_store_path() -> Path:
    """file where user-managed passwords and the ones extracted from the configuration are merged."""
    return Path(cmk.utils.paths.var_dir, "passwords_merged")


# This function and its questionable behavior of operating in-place on sys.argv is quasi-public.
# Many third party plugins rely on it, so we must not change it.
# One day, when we have a more official versioned API we can hopefully remove it.
def replace_passwords() -> None:
    sys.argv[:] = hack.resolve_password_hack(sys.argv, lookup)


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


def extract(password_id: PasswordId) -> str | None:
    """Translate the password store reference to the actual password"""
    staging_path = pending_password_store_path()
    if not isinstance(password_id, tuple):
        return load(staging_path).get(password_id)

    # In case we get a tuple, assume it was coming from a ValueSpec "IndividualOrStoredPassword"
    pw_type, pw_id = password_id
    if pw_type == "password":
        return pw_id
    if pw_type == "store":
        # TODO: Is this None really intended? Shouldn't we better raise an exception?
        return load(staging_path).get(pw_id)

    raise MKGeneralException("Unknown password type.")


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
    return lookup(core_password_store_path(LATEST_CONFIG), pw_id)


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
        _version, rest = (  # noqa: F841
            raw[: PasswordStore.VERSION_BYTE_LENGTH],
            raw[PasswordStore.VERSION_BYTE_LENGTH :],
        )
        salt, rest = (
            rest[: PasswordStore.SALT_LENGTH],
            rest[PasswordStore.SALT_LENGTH :],
        )
        nonce, rest = (
            rest[: PasswordStore.NONCE_LENGTH],
            rest[PasswordStore.NONCE_LENGTH :],
        )
        tag, encrypted = (
            rest[: TaggedCiphertext.TAG_LENGTH],
            rest[TaggedCiphertext.TAG_LENGTH :],
        )
        key = PasswordStoreSecret().derive_secret_key(salt)
        return aes_gcm_decrypt(key, nonce, TaggedCiphertext(ciphertext=encrypted, tag=tag))
