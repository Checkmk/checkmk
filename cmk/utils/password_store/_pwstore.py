#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import secrets
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal, NotRequired, TypedDict
from uuid import uuid4

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.exceptions import MKGeneralException
from cmk.password_store.v1_unstable import PasswordStore, Secret
from cmk.utils.global_ident_type import GlobalIdent

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


def _get_store_secret() -> Secret[bytes]:
    try:
        return Secret(cmk.utils.paths.password_store_secret_file.read_bytes())
    except FileNotFoundError:
        pass

    secret = Secret(secrets.token_bytes(32))
    cmk.utils.paths.password_store_secret_file.parent.mkdir(parents=True, exist_ok=True)
    cmk.utils.paths.password_store_secret_file.write_bytes(secret.reveal())
    return secret


def password_store_path() -> Path:
    """file where the user-managed passwords are stored."""
    return cmk.utils.paths.var_dir / "stored_passwords"


def active_secrets_path_site(relative_path: Path, config_path: Path | None = None) -> Path:
    """file where the passwords for use by the helpers are stored

    This is "frozen" in the state at config generation.
    Watch out: The created files might be re-used with the next configuration version,
    so replacing the reference to 'latest' by the actual versioned path is not currently possible.
    """
    if config_path is None:
        config_path = VersionedConfigPath.make_latest_path(cmk.utils.paths.omd_root)
    return config_path / relative_path


# this might not be the best place for this funtion. But for now it keeps dependencies lean.
# TODO: we need to split this up, and correctly handle "pending" vs "activated" password stores.
def active_secrets_path_relay(config_path: Path | None = None) -> Path:
    """file where the passwords for use by the relays helpers are stored

    This is "frozen" in the state at config generation.
    Watch out: The created files might be re-used with the next configuration version,
    so replacing the reference to 'latest' by the actual versioned path is not currently possible.
    """
    if config_path is None:
        config_path = VersionedConfigPath.make_latest_path(Path())
    return config_path / "secrets/active_secrets"


def pending_secrets_path_site() -> Path:
    """file where user-managed passwords and the ones extracted from the configuration are merged."""
    return cmk.utils.paths.var_dir / "passwords_merged"


def generate_ad_hoc_secrets_path(tmpdir: Path) -> Path:
    return tmpdir / f"passwords_adhoc_{uuid4()}"


# COMING SOON:
# active_secrets_path_relay()
# pending_secrets_path_relay()


# should accept Mapping[str, Secret[str]]
def save(passwords: Mapping[str, str], store_path: Path) -> None:
    """Save the passwords to the pre-activation path"""
    store_path.parent.mkdir(parents=True, exist_ok=True)
    sane_passwords = {
        # This is normally needed to not break the file format for things like gcp tokens.
        # The GUI does this automatically by having only one line of input field,
        # but other sources (like the REST API) use this function as well.
        k: Secret(v.replace("\n", ""))
        for k, v in passwords.items()
    }

    store.save_bytes_to_file(
        store_path, PasswordStore(_get_store_secret()).dump_bytes(sane_passwords)
    )


# TODO: this loads all passwords as strings. Avoid this.
def load(store_path: Path) -> dict[str, str]:
    return {k: v.reveal() for k, v in _load(store_path).items()}


def _load(store_path: Path) -> Mapping[str, Secret[str]]:
    try:
        store_path_bytes: bytes = store_path.read_bytes()
    except FileNotFoundError:
        return {}

    if not store_path_bytes:
        return {}
    return PasswordStore(_get_store_secret()).load_bytes(store_path_bytes)


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
            if (pw := _load(pending_secrets_path_site()).get(password_id)) is None:
                raise MKGeneralException(
                    "Password not found in pending password store. Please check the password store."
                )
            return pw.reveal()
        case _:
            raise MKGeneralException(
                f"Unknown password type {password}. Expected 'cmk_postprocessed'."
            )


def extract(password_id: PasswordId) -> str:
    """Translate the password store reference to the actual password. This function is likely
    to be used by third party plugins and should not be moved / changed in behaviour."""
    staging_path = pending_secrets_path_site()
    match password_id:
        case str():
            if (pw := _load(staging_path).get(password_id)) is None:
                raise MKGeneralException(
                    f"Password not found in '{staging_path}'. Please check the password store."
                )
            return pw.reveal()
        # In case we get a tuple, assume it was coming from a ValueSpec "IndividualOrStoredPassword"
        case ("password", pw):
            return pw
        case ("store", pw_id):
            if (pw := _load(staging_path).get(pw_id)) is None:
                raise MKGeneralException(
                    f"Password not found in '{staging_path}'. Please check the password store."
                )
            return pw.reveal()
        case _:
            raise MKGeneralException("Unknown password type.")


def make_staged_passwords_lookup() -> Callable[[str], str | None]:
    """Returns something similar to `extract`. Intended for internal use only."""
    # maybe we should pass this, but lets be consistent for now.
    staging_path = pending_secrets_path_site()
    return load(staging_path).get


def make_configured_passwords_lookup() -> Callable[[str], str | None]:
    """Returns something similar to `extract`. Intended for internal use only."""
    # maybe we should pass this, but lets be consistent for now.
    path = password_store_path()
    return load(path).get


def lookup(pw_file: Path, pw_id: str) -> str:
    """Look up the password with id <id> in the file <file> and return it.

    Raises:
        ValueError: If the password_id is not found in the password store.

    Returns:
        The password as found in the password store.
    """
    try:
        return _load(pw_file)[pw_id].reveal()
    except KeyError:
        # the fact that this is a dict is an implementation detail.
        # Let's make it a ValueError.
        raise ValueError(f"Password '{pw_id}' not found in {pw_file}")


def lookup_for_bakery(pw_id: str) -> str:
    return lookup(
        active_secrets_path_site(
            # Duplicated from cmk.base.core.active_config_layout.
            # But this function is depricated anyway.
            Path("stored_passwords"),
        ),
        pw_id,
    )
