#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This package contains cryptographic functionality for Checkmk.

It aims to provide a coherent, hard-to-misuse API. It should also serve as a facade to both
our crypto dependencies and python's built-in crypto utilities (like hashlib).
"""


import secrets
from typing import AnyStr, Final, Generic

from typing_extensions import assert_never


class Password(Generic[AnyStr]):
    """A human-readable password

    The plaintext password can be accessed via `.raw`. Note that raw passwords should never be
    logged without masking.
    """

    def __init__(self, password: AnyStr) -> None:
        if isinstance(password, bytes):
            nul = b"\0"
        elif isinstance(password, str):
            nul = "\0"
        else:
            assert_never(password)

        if nul in password:
            raise ValueError(f"Invalid password: {password!r}")
        self.raw: Final[AnyStr] = password

    @property
    def raw_bytes(self) -> bytes:
        """Return the raw password as bytes, utf-8-encoded in case it is a string"""
        match self.raw:
            case bytes():
                return self.raw
            case str():
                return self.raw.encode("utf-8")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Password):
            return NotImplemented
        return secrets.compare_digest(self.raw_bytes, other.raw_bytes)
