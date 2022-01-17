#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum
from zlib import decompress
from zlib import error as zlibError


class DecompressionError(Exception):
    ...


class Decompressor(Enum):
    ZLIB = "zlib"

    def __call__(self, data: bytes) -> bytes:
        """
        >>> from zlib import compress
        >>> Decompressor("zlib")(compress(b"blablub"))
        b'blablub'
        """
        return {Decompressor.ZLIB: Decompressor._zlib_decompress}[self](data)

    @staticmethod
    def _zlib_decompress(data: bytes) -> bytes:
        """
        >>> from zlib import compress
        >>> Decompressor._zlib_decompress(compress(b"blablub"))
        b'blablub'
        >>> Decompressor._zlib_decompress(b"blablub")
        Traceback (most recent call last):
            ...
        agent_receiver.decompression.DecompressionError: ...
        """
        try:
            return decompress(data)
        except zlibError as e:
            raise DecompressionError(f"Decompression with zlib failed: {e}") from e
