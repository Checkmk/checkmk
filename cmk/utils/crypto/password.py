#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import secrets
from dataclasses import dataclass
from enum import Enum
from typing import AnyStr, Final, Generic, Union

from cmk.utils.type_defs import assert_never


@dataclass
class PasswordPolicy:
    """A Password policy"""

    min_length: Union[int, None]
    min_groups: Union[int, None]

    Result = Enum("Result", ["OK", "TooShort", "TooSimple"])


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

    def verify_policy(self, policy: PasswordPolicy) -> PasswordPolicy.Result:
        # TooShort takes precedence over TooSimple
        if policy.min_length and self.char_count() < policy.min_length:
            return PasswordPolicy.Result.TooShort

        if min_groups := policy.min_groups:
            groups = {}
            # pylint seems to think as_string() might return None (match/case is hard?)
            for c in self.as_string():  # pylint: disable=not-an-iterable
                if c in "abcdefghijklmnopqrstuvwxyz":
                    groups["lcase"] = 1
                elif c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    groups["ucase"] = 1
                elif c in "0123456789":
                    groups["numbers"] = 1
                else:
                    groups["special"] = 1

            if sum(groups.values()) < min_groups:
                return PasswordPolicy.Result.TooSimple

        return PasswordPolicy.Result.OK

    @property
    def raw_bytes(self) -> bytes:
        """
        Return the raw password as bytes, UTF-8 encoded in case it is a string.

            >>> Password("💚✅").raw_bytes
            b'\\xf0\\x9f\\x92\\x9a\\xe2\\x9c\\x85'

        """
        if isinstance(self.raw, str):
            return self.raw.encode("utf-8")
        return self.raw

    def as_string(self) -> str:
        """
        Return the string representation of the password, UTF-8 decoded in case it's based on bytes.

            >>> Password(b"\\xf0\\x9f\\x92\\x9a\\xe2\\x9c\\x85").as_string()
            '💚✅'

        """
        if isinstance(self.raw, bytes):
            return self.raw.decode("utf-8")
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
