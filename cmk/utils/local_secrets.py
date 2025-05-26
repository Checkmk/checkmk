#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import hashlib
import secrets
from pathlib import Path
from typing import assert_never

from cmk.ccc import store
from cmk.ccc.user import UserId

from cmk.utils import paths

from cmk.crypto.password import Password
from cmk.crypto.secrets import LocalSecret, Secret


class AuthenticationSecret(LocalSecret):
    """Secret used to derive cookie authentication hash"""

    @property
    def path(self) -> Path:
        return paths.auth_secret_file


class PasswordStoreSecret(LocalSecret):
    """Secret used to obfuscate passwords in the password store

    Note: Previously these secrets were created as 256 letters and uppercase digits.
    These existing secrets will be loaded and used, even if they look different from
    the secrets created now.
    """

    @property
    def path(self) -> Path:
        return paths.password_store_secret_file

    def derive_secret_key(self, salt: bytes) -> bytes:
        """Derive a symmetric key from the local secret"""
        # TODO: in a future step (that requires migration of passwords) we could switch to HKDF.
        # Scrypt is slow by design but that isn't necessary here because the secret is not just a
        # password but "real" random data.
        # Note that key derivation and encryption/decryption of passwords is duplicated in omd
        # cmk_password_store.h and must be kept compatible!
        return hashlib.scrypt(self.secret.reveal(), salt=salt, n=2**14, r=8, p=1, dklen=32)


class SiteInternalSecret(LocalSecret):
    """Used to authenticate between site internal components, e.g. agent-receiver and rest_api"""

    @property
    def path(self) -> Path:
        return paths.site_internal_secret_file

    def check(self, other: Secret) -> bool:
        """Check if a given secret is the same as this one in a timing attack safe manner"""
        return self.secret.compare(other)


class AutomationUserSecret:
    """An automation user's login secret

    Note: this is not really a secret like the other secrets in this file an must not be used the
    same way. It's a (possibly randomly generated, possibly user provided) password.
    In particular, this means it cannot be used for cryptographic operations without proper
    password-based key derivation first.

    If possible, the goal is to remove this class (and file) entirely (CMK-12142), checking the
    password like other user passwords and storing it in the password store if necessary.
    """

    def __init__(self, user_id: UserId, profile_dir: Path | None = None) -> None:
        if profile_dir is None:
            profile_dir = paths.profile_dir
        self.path = profile_dir / user_id / "automation.secret"

    def read(self) -> str:
        """Read the secret from the user's "automation.secret" file.

        Raises an exception if the file does not exist or an empty secret has been read from the
        file.
        """
        # Note: stripping here is required because older code insisted on adding a newline at the
        # end of the file and strip that when reading. Would be nice to remove this but it would
        # need a migration. It's probably better to get rid of the file altogether (CMK-12142).
        if not (secret := self.path.read_text().strip()):
            raise ValueError(f"Secret loaded from {self.path} is empty")
        return secret

    def exists(self) -> bool:
        """Check if the secret file is present on disk"""
        return self.path.is_file()

    def save(self, secret: str) -> None:
        """Write the secret to the user's "automation.secret" file"""
        self.path.write_text(secret)

    def delete(self) -> None:
        """Delete the secret file, ignore missing files"""
        self.path.unlink(missing_ok=True)

    def check(self, other: str) -> bool:
        """Check if a given secret is the same as this one in a timing attack safe manner"""
        return secrets.compare_digest(self.read().encode("utf-8"), other.encode("utf-8"))


class DistributedSetupSecret:
    """The secret used by the central site to sync the config"""

    # Todo: why are we not generating this anyways? If somebody wants to access the deploy_remote
    # site and no secret was set yet, access will be blocked... That is IMHO the only advantage

    def __init__(self) -> None:
        self.password = (
            Password(pw)
            if (pw := store.load_object_from_file(self.path, default=None)) is not None
            else None
        )
        self._secret = None if self.password is None else Secret(self.password.raw_bytes)

    @property
    def secret(self) -> Secret:
        if self._secret is None:
            raise ValueError("Secret was not set yet, so nothing to read yet")
        return self._secret

    @property
    def path(self) -> Path:
        return paths.var_dir / "wato" / "automation_secret.mk"

    def read_or_create(self) -> Password:
        if self.password is None:
            self.regenerate()
        assert self.password is not None
        return self.password

    def regenerate(self) -> None:
        """Generate a new secret and write it to disk.

        If the file already exists, it will be overwritten.
        """
        self.password = Password(secrets.token_urlsafe(32))
        self._secret = Secret(self.password.raw_bytes)
        store.save_object_to_file(self.path, self.password.raw)

    def compare(self, other: Password | Secret) -> bool:
        if self.password is None or self._secret is None:
            return False
        match other:
            case Password():
                return self.password == other
            case Secret():
                return self.secret.compare(other)
            case _ as unreachable:
                assert_never(unreachable)
