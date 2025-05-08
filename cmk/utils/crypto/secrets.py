#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path
from typing import AnyStr

import cmk.utils.paths as paths
from cmk.utils.user import UserId


class Secret:
    def __init__(self, value: bytes) -> None:
        if not value:
            # This is a safeguard against creating empty secrets, which would be bad for most
            # cryptographic operations.
            raise ValueError("Cannot create empty secrets")

        self._value = value

    def compare(self, other: Secret) -> bool:
        return secrets.compare_digest(self._value, other._value)

    @property
    def b64_str(self) -> str:
        return base64.b64encode(self._value).decode("ascii")

    @classmethod
    def from_b64(cls, b64_value: AnyStr) -> Secret:
        return cls(base64.b64decode(b64_value))


class _LocalSecret(ABC):
    def __init__(self) -> None:
        """Read the secret; create it if the file doesn't exist.

        Loading an existing but empty file raises an error.
        """
        # TODO: reading and writing could use some locking, once our locking utilities are improved
        if self.path.exists() and (secret := self.path.read_bytes()):
            self.secret = secret
            return

        self.regenerate()

    def regenerate(self) -> None:
        """generate new secret and store it

        this does not care if the secret already exists"""

        self.secret = secrets.token_bytes(32)
        # TODO: mkdir is probably not really required here, just some cmc test failing.
        #       Better way would be to fix the test setup.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(mode=0o600)
        self.path.write_bytes(self.secret)

    @property
    @abstractmethod
    def path(self) -> Path:
        raise NotImplementedError

    def hmac(self, msg: str) -> str:
        """Calculate the HMAC(SHA256) of `msg` using this secret and return the digest in hex"""
        return hmac.new(key=self.secret, msg=msg.encode("utf-8"), digestmod=sha256).hexdigest()

    def derive_secret_key(self, salt: bytes) -> bytes:
        """Derive a symmetric key from the local secret"""
        # TODO: in a future step (that requires migration of passwords) we could switch to HKDF.
        # Scrypt is slow by design but that isn't necessary here because the secret is not just a
        # password but "real" random data.
        # Note that key derivation and encryption/decryption of passwords is duplicated in omd
        # cmk_password_store.h and must be kept compatible!
        return hashlib.scrypt(self.secret, salt=salt, n=2**14, r=8, p=1, dklen=32)


class AuthenticationSecret(_LocalSecret):
    """Secret used to derive cookie authentication hash"""

    @property
    def path(self) -> Path:
        return paths.auth_secret_file


class PasswordStoreSecret(_LocalSecret):
    """Secret used to obfuscate passwords in the password store

    Note: Previously these secrets were created as 256 letters and uppercase digits.
    These existing secrets will be loaded and used, even if they look different from
    the secrets created now.
    """

    @property
    def path(self) -> Path:
        return paths.password_store_secret_file


class EncrypterSecret(_LocalSecret):
    """Secret used to encrypt and authenticate secrets passed _through_ the GUI"""

    # TODO: Use a different secret for separation of concerns. If possible, rotate often. CMK-11925
    @property
    def path(self) -> Path:
        return paths.auth_secret_file


class SiteInternalSecret(_LocalSecret):
    """Used to authenticate between site internal components, e.g. agent-receiver and rest_api"""

    @property
    def path(self) -> Path:
        return paths.site_internal_secret_file

    def check(self, other: Secret) -> bool:
        """Check if a given secret is the same as this one in a timing attack safe manner"""
        return Secret(self.secret).compare(other)


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
