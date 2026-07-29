#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import math
import tarfile
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Final, IO, Literal


def fmt_bytes(bytes_val: int, unit: str | None = None) -> str:
    """
    Formats a byte count into a human-readable string (TB, GB, MB, KB, or B).

    Args:
        bytes_val: The number of bytes (as an integer).
        unit: If provided, this string will replace the automatically
              determined unit (e.g., 'MB') in the output string.
              This parameter does NOT affect the scaling calculation.

    Returns:
        A formatted string (e.g., "1.45 MB").
    """
    if bytes_val < 0:
        return "Invalid Input"

    if bytes_val == 0:
        return f"0 {unit or 'B'}"
    power_units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    try:
        power = math.floor(math.log(bytes_val, 1024))
    except ValueError:
        power = 0
    power = min(power, len(power_units) - 1)
    value = bytes_val / (1024**power)
    display_unit = unit if unit is not None else power_units[power]
    if power == 0:
        return f"{int(value)} {display_unit}"
    return f"{value:.2f} {display_unit}"


class NotAValidArchive(ValueError): ...


class UnpackedArchiveTooLargeError(ValueError): ...


class SecurityViolation(ValueError): ...


TarFilterCallable = Callable[[tarfile.TarInfo, str], tarfile.TarInfo | None]
FilterType = Literal["fully_trusted", "tar", "data"] | TarFilterCallable
Compression = Literal["gz", "*"]

_TarReadMode = Literal["r|gz", "r|*", "r:gz", "r:*"]
_GIB: Final = 1024**3


@dataclass(frozen=True, kw_only=True)
class ArchiveLimits:
    """The limits enforced while reading an archive."""

    size_limit_bytes: int = 10 * _GIB
    file_limit: int = 100_000
    per_file_limit: int = 2 * _GIB
    raw_limit_bytes: int = 1 * _GIB
    allow_symlinks: bool = True

    def validate_member(self, member: tarfile.TarInfo) -> None:
        if member.name == "":
            # This should never happen
            raise NotAValidArchive("Archive member name is cannot be empty")
        if not self.allow_symlinks and (member.islnk() or member.issym()):
            raise SecurityViolation(f"Symlink or hardlink not allowed: {member.name}")
        if member.ischr() or member.isblk() or member.isfifo():
            raise SecurityViolation(f"Special file not allowed: {member.name}")
        if member.size > self.per_file_limit:
            raise UnpackedArchiveTooLargeError(
                f"File {member.name} exceeds per-file size limit: "
                f"({fmt_bytes(member.size)} > {fmt_bytes(self.per_file_limit)})"
            )

    def validate_file_count(self, count: int) -> None:
        if count > self.file_limit:
            raise UnpackedArchiveTooLargeError(f"Archive contains too many files ({count})")

    def validate_unpacked_size(self, size: int) -> None:
        if size > self.size_limit_bytes:
            raise UnpackedArchiveTooLargeError(
                f"Archive exceeds total size limit: "
                f"({fmt_bytes(size)} > {fmt_bytes(self.size_limit_bytes)})"
            )

    def validate_compressed_size(self, size: int) -> None:
        if size > self.raw_limit_bytes:
            raise UnpackedArchiveTooLargeError(
                f"Compressed archive too large: "
                f"({fmt_bytes(size)} > {fmt_bytes(self.raw_limit_bytes)})"
            )


DEFAULT_ARCHIVE_LIMITS: Final = ArchiveLimits()


class BaseSafeTarFile:
    """Base wrapper for TarFile with enforced security checks.

    Prevents path traversal, symlink attacks and oversized archives.
    """

    def __init__(self, tar: tarfile.TarFile, limits: ArchiveLimits):
        self._tar = tar
        self._limits = limits
        self._member_iter = iter(self._tar)

    def __iter__(self) -> Iterator[tarfile.TarInfo]:
        return self

    def __next__(self) -> tarfile.TarInfo:
        return next(self._member_iter)

    def extract(
        self, member: tarfile.TarInfo | str, path: str | Path = ".", tar_filter: FilterType = "data"
    ) -> None:
        """
        Safely extract an archive to the desired path.
        """
        path = Path(path).resolve()
        member_name = member.name if isinstance(member, tarfile.TarInfo) else member
        resolved = (path / member_name).resolve()
        if not resolved.is_relative_to(path):
            raise SecurityViolation(f"Path traversal attempt: {member_name}")
        self._tar.extract(member, path=path, filter=tar_filter)

    def extractmember(self, member: tarfile.TarInfo | str) -> IO[bytes] | None:
        return self._tar.extractfile(member)

    def extractall(self, dest: Path | str) -> None:
        """
        Safely extract a whole archive to the disk
        """
        if isinstance(dest, str):
            dest = Path(dest)
        dest = dest.resolve()
        for member in self:
            self.extract(member, path=dest)

    def extractfile_by_name(
        self,
        target_file: str,
    ) -> IO[bytes] | None:
        """
        Safely extract a single file from the archive in memory.
        Raises FileNotFoundError if the file does not exist.
        """
        if not target_file:
            return None
        for member in self:
            if member.name == target_file:
                return self.extractmember(member)
        return None

    def __getattr__(self, name: str) -> Any:  # type: ignore[explicit-any]
        return getattr(self._tar, name)

    def __enter__(self) -> "BaseSafeTarFile":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._tar.close()


class SafeStreamedTarFile(BaseSafeTarFile):
    """Safe wrapper around TarFile in streaming mode (r|gz).

    Validates incrementally during iteration. There is a cursor: seeking backwards is not possible
    and once it reaches EOF the archive has to be reopened for a second pass.
    """

    def __init__(self, tar: tarfile.TarFile, limits: ArchiveLimits):
        super().__init__(tar, limits)
        self._total_size = 0
        self._file_count = 0

    def __next__(self) -> tarfile.TarInfo:
        # Get next member from underlying tar
        member = next(self._member_iter)
        self._file_count += 1
        self._total_size += member.size
        self._limits.validate_file_count(self._file_count)
        self._limits.validate_unpacked_size(self._total_size)
        self._limits.validate_member(member)
        return member

    def getmembers(self) -> None:
        raise TypeError("getmembers() not supported in streaming-safe mode; use iteration instead")


class SafeIndexedTarFile(BaseSafeTarFile):
    """Safe wrapper around TarFile in indexed mode (r:gz).

    Validates all members eagerly on open, which requires reading the whole archive into memory.
    Prefer streaming mode where possible.
    """

    def __init__(self, tar: tarfile.TarFile, limits: ArchiveLimits) -> None:
        super().__init__(tar, limits)
        members = tar.getmembers()

        limits.validate_file_count(len(members))
        limits.validate_unpacked_size(sum(m.size for m in members))
        for m in members:
            limits.validate_member(m)
        self._member_iter = iter(members)


@contextmanager
def open_bytes(
    raw: bytes,
    *,
    streaming: bool = True,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeStreamedTarFile | SafeIndexedTarFile]:
    with open_buffer(
        io.BytesIO(raw), streaming=streaming, compression=compression, limits=limits
    ) as tar:
        yield tar


@contextmanager
def open_buffer(
    buffer: IO[bytes],
    *,
    streaming: bool = True,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeStreamedTarFile | SafeIndexedTarFile]:
    with _open_buffer(buffer, _mode(compression, streaming=streaming), limits) as tar:
        yield (SafeStreamedTarFile(tar, limits) if streaming else SafeIndexedTarFile(tar, limits))


@contextmanager
def open_path(
    path: Path,
    *,
    streaming: bool = True,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeStreamedTarFile | SafeIndexedTarFile]:
    with _open_path(path, _mode(compression, streaming=streaming), limits) as tar:
        yield (SafeStreamedTarFile(tar, limits) if streaming else SafeIndexedTarFile(tar, limits))


def validate_bytes(
    raw: bytes,
    *,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> None:
    """Validate an archive without writing anything to disk.

    Streams through all members and enforces the limits.
    """
    with open_bytes(raw, compression=compression, limits=limits) as archive:
        for _ in archive:
            ...


@contextmanager
def _open_buffer(
    buffer: IO[bytes], mode: _TarReadMode, limits: ArchiveLimits
) -> Generator[tarfile.TarFile]:
    try:
        limits.validate_compressed_size(_buffer_size(buffer))
        buffer.seek(0)
        with tarfile.open(fileobj=buffer, mode=mode) as tar:
            yield tar
    except tarfile.ReadError as exc:
        raise NotAValidArchive from exc


@contextmanager
def _open_path(path: Path, mode: _TarReadMode, limits: ArchiveLimits) -> Generator[tarfile.TarFile]:
    try:
        limits.validate_compressed_size(path.stat().st_size)
        with tarfile.open(name=path, mode=mode) as tar:
            yield tar
    except tarfile.ReadError as exc:
        raise NotAValidArchive from exc


def _buffer_size(buffer: IO[bytes]) -> int:
    current_pos = buffer.tell()
    buffer.seek(0, 2)
    size = buffer.tell()
    buffer.seek(current_pos)
    return size


def _mode(compression: Compression, *, streaming: bool) -> _TarReadMode:
    # NOTE: mypy currently doesn't narrow on tuples, so we have to use the
    # slightly less readable if/else cascade below.
    return (
        ("r|gz" if compression == "gz" else "r|*")
        if streaming
        else ("r:gz" if compression == "gz" else "r:*")
    )
