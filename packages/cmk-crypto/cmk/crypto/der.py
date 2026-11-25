# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrappers for X.690 DER-encoded data."""

import base64
from typing import Self

from . import MKCryptoException


class DERDecodingError(MKCryptoException):
    pass


class _DERData:
    """Some data serialized in DER format.

    Offers convenience properties to access the data as BASE64 string or bytes.
    """

    _data: bytes

    def __init__(self, der_bytes: bytes) -> None:
        self._data = der_bytes

    @classmethod
    def from_base64(cls, base64_str: str | bytes) -> Self:
        return cls(base64.b64decode(base64_str))

    @classmethod
    def from_bytes(cls, der_bytes: bytes) -> Self:
        return cls(der_bytes)

    @property
    def base64_str(self) -> str:
        return base64.b64encode(self._data).decode()

    @property
    def bytes(self) -> bytes:
        return self._data
