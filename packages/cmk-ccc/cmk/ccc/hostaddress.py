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

    def __new__(cls, text: str) -> Self:
        """Construct a new HostAddress object

        Raises:
            - ValueError: whenever the given text is not a valid HostAddress

        >>> HostAddress("checkmk.com")
        'checkmk.com'

        >>> HostAddress("::1")
        '::1'

        >>> HostAddress("Â")
        Traceback (most recent call last):
            ...
        ValueError: invalid host address: 'Â'

        >>> HostAddress(".")
        Traceback (most recent call last):
            ...
        ValueError: invalid host address: '.'
        """
        if len(text) > 240:
            # Ext4 and others allow filenames of up to 255 bytes.
            # As we add prefixes and/or suffixes, the number has to be way lower.
            # 240 seems to be OK to still be able to delete a host if it causes
            # trouble elsewhere
            raise ValueError(f"host address too long: {text[:16] + '…'!r}")

        try:
            ipaddress.ip_address(text)
        except ValueError:
            # TODO: Why do we want to allow empty host names?
            if text and not HostAddress.REGEX_HOST_NAME.match(text):
                raise ValueError(f"invalid host address: {text!r}")

        return super().__new__(cls, text)

    @classmethod
    def parse(cls, x: object) -> Self:
        if isinstance(x, cls):
            return x
        if isinstance(x, str):
            return cls(x)
        raise ValueError(f"invalid host address: {x!r}")

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


# Let us be honest here, we do not actually make a difference
# between HostAddress and HostName in our code.
HostName: TypeAlias = HostAddress
