#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import secrets
import string
from typing import AnyStr, Final, Generic, NewType

from typing_extensions import assert_never


class Password(Generic[AnyStr]):
    """A human-readable password

    The plaintext password can be accessed via `.raw`. Note that raw passwords should never be
    logged without masking.
    """

    @classmethod
    def random(cls, length: int) -> Password[str]:
        """Generate a random password

        Important: do not use this to generate cryptographic secrets. This function is intended
        to generate default that can be entered (and hopefully changed) by users. In order to
        obtain cryptographic key material, a key derivation function is necessary.

        The generated password may contain digits and upper- and lowercase ascii letters.
        """
        if length < 0:
            raise ValueError("Password length must not be negative")
        alphabet = string.ascii_letters + string.digits
        return Password("".join(secrets.choice(alphabet) for _ in range(length)))

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
        """
        Return the raw password as bytes, UTF-8 encoded in case it is a string.

            >>> Password("💚✅").raw_bytes
            b'\\xf0\\x9f\\x92\\x9a\\xe2\\x9c\\x85'

        """
        match self.raw:
            case bytes():
                return self.raw
            case str():
                return self.raw.encode("utf-8")

    def as_string(self) -> str:
        """
        Return the string representation of the password, UTF-8 decoded in case it's based on bytes.

            >>> Password(b"\\xf0\\x9f\\x92\\x9a\\xe2\\x9c\\x85").as_string()
            '💚✅'

        """
        match self.raw:
            case bytes():
                return self.raw.decode("utf-8")
            case str():
                return self.raw

    def char_count(self) -> int:
        """
        Return the length of password as the number of characters.

        Byte-based Passwords will be UTF-8 decoded to count the characters. This might not make
        sense for randomly generated passwords based on bytes. Use `len(self.raw_bytes)` if you
        care for the number of bytes.

        This means:

            >>> Password("💚✅").char_count()
            2
            >>> Password(b"\\xf0\\x9f\\x92\\x9a\\xe2\\x9c\\x85").char_count()  # "💚✅" as well
            2
            >>> len(Password("💚✅").raw_bytes)
            7

        More examples:

            >>> Password("abc").char_count()
            3
            >>> Password(b"abc").char_count()
            3
            >>> Password("").char_count()
            0
        """
        return len(self.as_string())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Password):
            return NotImplemented
        return secrets.compare_digest(self.raw_bytes, other.raw_bytes)


PasswordHash = NewType("PasswordHash", str)
