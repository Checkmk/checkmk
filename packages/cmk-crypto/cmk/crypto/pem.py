#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helpers for dealing with PEM-encoded data"""

from . import MKCryptoException


class PEMDecodingError(MKCryptoException):
    """Decoding a PEM has failed.

    Possible reasons:
     - PEM structure is invalid
     - decoded content is not as expected
     - PEM is encrypted and the password is wrong
    """


class _PEMData:
    """Some data serialized in PEM format.

    Offers convenience properties to access the data as str or bytes.
    """

    def __init__(self, pem: str | bytes) -> None:
        if isinstance(pem, str):
            self._data = pem.encode()
        elif isinstance(pem, bytes):
            self._data = pem
        else:
            raise TypeError("PEM must either be bytes or str")

    @property
    def str(self) -> str:
        return self._data.decode()

    @property
    def bytes(self) -> bytes:
        return self._data
