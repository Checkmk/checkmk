#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ipaddress
import itertools
import re
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Final, Self, TypeAlias

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema, CoreSchema

__all__ = ["HostAddress", "Hosts", "HostName"]


@dataclass(frozen=True)
class Hosts:
    hosts: Sequence[HostName]
    clusters: Sequence[HostName]
    shadow_hosts: Sequence[HostName]

    def duplicates(self, /, pred: Callable[[HostName], bool]) -> Iterable[HostName]:
        return (hn for hn, count in Counter(hn for hn in self if pred(hn)).items() if count > 1)

    def __iter__(self) -> Iterator[HostName]:
        return itertools.chain(self.hosts, self.clusters, self.shadow_hosts)


class HostAddress(str):
    """A Checkmk HostAddress or HostName"""

    _ALLOWED_CHARS_CLASS: Final = r"-0-9a-zA-Z_."
    REGEX_HOST_NAME: Final = re.compile(rf"^\w[{_ALLOWED_CHARS_CLASS}]*$", re.ASCII)
    REGEX_INVALID_CHAR: Final = re.compile(rf"[^{_ALLOWED_CHARS_CLASS}]")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: object, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate_hostname,
            handler(str),
        )

    @staticmethod
    def validate(text: str) -> None:
        """Check if it is a HostAddress/HostName

        >>> HostAddress.validate(".")
        Traceback (most recent call last):
            ...
        ValueError: Invalid hostaddress: '.'

        >>> HostAddress.validate("checkmk.com")
        >>> HostAddress.validate("::1")

        >>> HostAddress.validate("Â")
        Traceback (most recent call last):
            ...
        ValueError: Invalid hostaddress: 'Â'
        """
        HostAddress.validate_hostname(text)

    @staticmethod
    def validate_hostname(text: str) -> str:
        if text in ("", "_", "_VANILLA"):
            return text

        if len(text) > 254:
            # ext4 and others allow filenames of up to 255 bytes
            raise ValueError(f"HostName too long: {text[:16] + '…'!r}")

        try:
            ipaddress.ip_address(text)
            return text
        except ValueError:
            pass

        if not HostAddress.REGEX_HOST_NAME.match(text):
            raise ValueError(f"Invalid hostaddress: {text!r}")

        return text

    @staticmethod
    def is_valid(text: str) -> bool:
        try:
            HostAddress.validate(text)
            return True
        except ValueError:
            return False

    @classmethod
    def project_valid(cls, text: str) -> Self:
        """Create a valid host name from input.

        This is a projection in the sense that the function is not injective.
        Different input might be projected onto the same output.

        Raises:
            - ValueError: whenever the given text is not a valid HostAddress
            even after replacing invalid characters.

        """
        return cls(cls.REGEX_INVALID_CHAR.sub("_", text))

    def __new__(cls, text: str) -> Self:
        """Construct a new HostAddress object

        Raises:
            - ValueError: whenever the given text is not a valid HostAddress
        """
        cls.validate(text)
        return super().__new__(cls, text)


# Let us be honest here, we do not actually make a difference
# between HostAddress and HostName in our code.
HostName: TypeAlias = HostAddress
