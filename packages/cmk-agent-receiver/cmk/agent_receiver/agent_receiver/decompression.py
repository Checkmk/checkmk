#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import zlib
from enum import Enum

MAX_SIZE_AGENT_DATA = 512 * 1024**2  # 512 MiB


class DecompressionError(Exception): ...


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
        packages.cmk-agent-receiver.cmk.agent_receiver.agent_receiver.decompression.DecompressionError: ...
        """
        decompressor = zlib.decompressobj()
        try:
            uncompressed = decompressor.decompress(data, max_length=MAX_SIZE_AGENT_DATA)
            if decompressor.unconsumed_tail:
                raise DecompressionError("Decompression failed: data is too long")
            return uncompressed
        except zlib.error as e:
            raise DecompressionError(f"Decompression with zlib failed: {e}") from e
