#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from io import UnsupportedOperation
from types import TracebackType
from typing import IO


class BufferWithCopy(IO[bytes]):
    def __init__(self, buffer: IO[bytes]) -> None:
        super().__init__()
        self._buffer = buffer
        self._seen = bytearray()
        self._reset_called = False

    def read(self, size: int = -1) -> bytes:
        if self._reset_called:
            raise NotImplementedError()
        chunk = self._buffer.read(size)
        self._seen.extend(chunk)
        return chunk

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        # tarfile.open always closes the buffer, which we want to avoid.
        pass

    def stream_content(self) -> Iterator[bytes | bytearray]:
        if self._reset_called:
            raise NotImplementedError()
        self._reset_called = True
        if self._seen:
            yield self._seen
        while chunk := self._buffer.read(65536):
            yield chunk

    # Implemenations below only to satisfy `IO[bytes]`

    @property
    def mode(self) -> str:
        return self._buffer.mode

    @property
    def name(self) -> str:
        return self._buffer.name

    @property
    def closed(self) -> bool:
        return self._buffer.closed

    def fileno(self) -> int:
        return self._buffer.fileno()

    def flush(self) -> None:
        return self._buffer.flush()

    def isatty(self) -> bool:
        return self._buffer.isatty()

    def readline(self, limit: int = -1) -> bytes:
        return self._buffer.readline(limit)

    def readlines(self, hint: int = -1) -> list[bytes]:
        return self._buffer.readlines(hint)

    def seek(self, *_: object) -> int:
        raise UnsupportedOperation("underlying stream is not seekable")

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        raise UnsupportedOperation("underlying stream is not seekable")

    def truncate(self, _: object = -1) -> int:
        raise UnsupportedOperation("truncate")

    def writable(self) -> bool:
        return False

    def write(self, _: object, /) -> int:
        raise UnsupportedOperation("not writable")

    def writelines(self, _: object, /) -> None:
        raise UnsupportedOperation("not writable")

    def __enter__(self) -> IO[bytes]:
        return self._buffer.__enter__()

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return self._buffer.__exit__(type_, value, traceback)

    def __next__(self) -> bytes:
        return self._buffer.__next__()

    def __iter__(self) -> Iterator[bytes]:
        return self._buffer.__iter__()
