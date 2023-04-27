#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import secrets
import string
from dataclasses import dataclass
from enum import Enum
from typing import Final, Union


@dataclass
class PasswordPolicy:
    """A Password policy"""

    min_length: Union[int, None]
    min_groups: Union[int, None]

    Result = Enum("Result", ["OK", "TooShort", "TooSimple"])


class Password:
    """A human-readable password

    The plaintext password can be accessed via `.raw`. Note that raw passwords should never be
    logged without masking.
    """

    def __init__(self, password: str) -> None:
        if "\0" in password:
            raise ValueError("Password must not contain null bytes")
        if password == "":
            raise ValueError("Password must not be empty")
        self.raw: Final[str] = password

    def verify_policy(self, policy: PasswordPolicy) -> PasswordPolicy.Result:
        # TooShort takes precedence over TooSimple
        if policy.min_length and len(self) < policy.min_length:
            return PasswordPolicy.Result.TooShort

        if min_groups := policy.min_groups:
            groups = set()
            for c in self.raw:
                if c in string.ascii_lowercase:
                    groups.add("lowercase")
                elif c in string.ascii_uppercase:
                    groups.add("uppercase")
                elif c in string.digits:
                    groups.add("digit")
                else:
                    groups.add("special")

            if len(groups) < min_groups:
                return PasswordPolicy.Result.TooSimple

        return PasswordPolicy.Result.OK

    @property
    def raw_bytes(self) -> bytes:
        """
        Return the raw password as bytes, UTF-8 encoded in case it is a string.

            >>> Password("💚✅").raw_bytes
            b'\\xf0\\x9f\\x92\\x9a\\xe2\\x9c\\x85'
            >>> Password("💚✅").raw
            '💚✅'

        """
        return self.raw.encode("utf-8")

    def __len__(self) -> int:
        """
        Return the length of password as the number of characters.

        Note that unicode characters represented by multiple bytes still only count as one
        character. Use `len(self.raw_bytes)` if you care for the number of bytes.

        This means:

            >>> len(Password("💚✅"))
            2
            >>> len(Password("💚✅").raw_bytes)
            7
            >>> len(Password("abc"))
            3
        """
        return len(self.raw)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Password):
            return False
        return secrets.compare_digest(self.raw_bytes, other.raw_bytes)
