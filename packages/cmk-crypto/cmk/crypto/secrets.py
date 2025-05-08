#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005
"""Helper classes for secrets"""

from __future__ import annotations

import base64
import hmac
import secrets
from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path
from typing import AnyStr


class Secret:
    """A class for cryptographic secrets.

    Similar to passwords, but suitable for cryptographic operations and not for human use.
    """

    def __init__(self, value: bytes) -> None:
        if not value:
            # This is a safeguard against creating empty secrets, which would be bad for most
            # cryptographic operations.
            raise ValueError("Cannot create empty secrets")

        self._value = value

    def compare(self, other: Secret) -> bool:
        """Check if a given secret is the same as this one in a timing attack safe manner.

        You should use this method instead of `==` to compare secrets.
        """
        return secrets.compare_digest(self.reveal(), other.reveal())

    @property
    def b64_str(self) -> str:
        return base64.b64encode(self._value).decode("ascii")

    @classmethod
    def from_b64(cls, b64_value: AnyStr) -> Secret:
        return cls(base64.b64decode(b64_value))

    @classmethod
    def generate(cls, length: int = 32) -> Secret:
        return cls(secrets.token_bytes(length))

    def hmac(self, msg: bytes) -> bytes:
        """Calculate the HMAC(SHA256) of `msg` using this secret and return the digest in hex"""
        return hmac.new(key=self._value, msg=msg, digestmod=sha256).digest()

    def reveal(self) -> bytes:
        return self._value


class LocalSecret(ABC):
    """Base class for secrets that are stored locally on disk"""

    def __init__(self) -> None:
        """Read the secret.

        If the file at `self.path` does not exist or is empty, a new secret will be generated.
        """
        if self.path.exists() and (secret := self.path.read_bytes()):
            self.secret = Secret(secret)
            return

        self.regenerate()

    @property
    @abstractmethod
    def path(self) -> Path:
        """The path to the file where the secret is stored"""
        raise NotImplementedError

    def regenerate(self) -> None:
        """Generate a new secret and write it to disk.

        If the file already exists, it will be overwritten.
        """
        self.secret = Secret.generate(32)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(mode=0o600)
        self.path.write_bytes(self.secret.reveal())
