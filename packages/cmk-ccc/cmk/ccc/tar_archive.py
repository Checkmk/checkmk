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
from typing import Final, IO, Literal


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


class SafeStreamedTarFile:
    """Safe wrapper around TarFile in streaming mode (r|gz).

    Validates incrementally during iteration, which is therefore the only way to reach a member:
    seeking backwards is impossible, so members become available in archive order only and the
    archive has to be reopened for a second pass.
    """

    def __init__(self, tar: tarfile.TarFile, limits: ArchiveLimits, name: str | None) -> None:
        self._tar = tar
        self._limits = limits
        self._name = name
        self._member_iter = iter(tar)
        self._total_size = 0
        self._file_count = 0

    @property
    def name(self) -> str | None:
        """The path the archive was read from, if it was read from disk."""
        return self._name

    def __iter__(self) -> Iterator[tarfile.TarInfo]:
        return self

    def __next__(self) -> tarfile.TarInfo:
        member = next(self._member_iter)
        self._file_count += 1
        self._total_size += member.size
        self._limits.validate_file_count(self._file_count)
        self._limits.validate_unpacked_size(self._total_size)
        self._limits.validate_member(member)
        return member

    def extractall(self, dest: Path | str) -> None:
        """
        Safely extract the remaining members of the archive to the disk
        """
        for member in self:
            _extract_to_disk(self._tar, member, Path(dest), "data")

    def extractfile_by_name(self, target_file: str) -> IO[bytes] | None:
        """
        Safely extract a single file from the archive in memory. Returns None if the archive holds
        no such file, or if the member has no payload, e.g. because it is a directory or a link.

        Searching advances the cursor, so only members ahead of it can be found and the result has
        to be read before iteration continues.
        """
        if not target_file:
            return None
        for member in self:
            if member.name == target_file:
                return _payload(self._tar, member)
        return None

    def __enter__(self) -> SafeStreamedTarFile:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._tar.close()


class SafeIndexedTarFile:
    """Safe wrapper around TarFile in indexed mode (r:gz).

    Validates all members eagerly on open and keeps them, so they stay accessible in any order and
    iteration can be repeated.
    """

    def __init__(self, tar: tarfile.TarFile, limits: ArchiveLimits, name: str | None) -> None:
        members = tar.getmembers()
        limits.validate_file_count(len(members))
        limits.validate_unpacked_size(sum(m.size for m in members))
        for member in members:
            limits.validate_member(member)

        self._tar = tar
        self._name = name
        self._members: Final = members

    @property
    def name(self) -> str | None:
        """The path the archive was read from, if it was read from disk."""
        return self._name

    def __iter__(self) -> Iterator[tarfile.TarInfo]:
        return iter(self._members)

    def getmembers(self) -> list[tarfile.TarInfo]:
        return list(self._members)

    def extract(
        self, member: tarfile.TarInfo, path: str | Path = ".", tar_filter: FilterType = "data"
    ) -> None:
        """
        Safely extract a single member to the desired path
        """
        _extract_to_disk(self._tar, member, Path(path), tar_filter)

    def __enter__(self) -> SafeIndexedTarFile:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._tar.close()


@contextmanager
def open_bytes_streaming(
    raw: bytes,
    *,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeStreamedTarFile]:
    with open_buffer_streaming(io.BytesIO(raw), compression=compression, limits=limits) as tar:
        yield tar


@contextmanager
def open_bytes_indexed(
    raw: bytes,
    *,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeIndexedTarFile]:
    with open_buffer_indexed(io.BytesIO(raw), compression=compression, limits=limits) as tar:
        yield tar


@contextmanager
def open_buffer_streaming(
    buffer: IO[bytes],
    *,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeStreamedTarFile]:
    with _open_buffer(buffer, _streaming_mode(compression), limits) as tar:
        yield SafeStreamedTarFile(tar, limits, None)


@contextmanager
def open_buffer_indexed(
    buffer: IO[bytes],
    *,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeIndexedTarFile]:
    with _open_buffer(buffer, _indexed_mode(compression), limits) as tar:
        yield SafeIndexedTarFile(tar, limits, None)


@contextmanager
def open_path_streaming(
    path: Path,
    *,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeStreamedTarFile]:
    with _open_path(path, _streaming_mode(compression), limits) as tar:
        yield SafeStreamedTarFile(tar, limits, str(path))


@contextmanager
def open_path_indexed(
    path: Path,
    *,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> Generator[SafeIndexedTarFile]:
    with _open_path(path, _indexed_mode(compression), limits) as tar:
        yield SafeIndexedTarFile(tar, limits, str(path))


def validate_bytes(
    raw: bytes,
    *,
    compression: Compression = "gz",
    limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
) -> None:
    """Validate an archive without writing anything to disk.

    Streams through all members and enforces the limits.
    """
    with open_bytes_streaming(raw, compression=compression, limits=limits) as archive:
        for _ in archive:
            ...


def _extract_to_disk(
    tar: tarfile.TarFile, member: tarfile.TarInfo, dest: Path, tar_filter: FilterType
) -> None:
    """Write a single member below dest, refusing to escape it.

    Every write to disk goes through here. The member has to be one the calling wrapper obtained
    itself: resolving one by name is deliberately not offered, since tarfile would answer that by
    reading the whole archive index, bypassing the wrapper's validation.
    """
    dest = dest.resolve()
    if not (dest / member.name).resolve().is_relative_to(dest):
        raise SecurityViolation(f"Path traversal attempt: {member.name}")
    tar.extract(member, path=dest, filter=tar_filter)


def _payload(tar: tarfile.TarFile, member: tarfile.TarInfo) -> IO[bytes] | None:
    """Read a member in memory, or None if it has no payload of its own.

    Only regular files carry one, and the streaming mode cannot even hand out anything else:
    tarfile raises a StreamError for a (sym)link because resolving it would mean seeking to the
    target.
    """
    return tar.extractfile(member) if member.isfile() else None


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


def _streaming_mode(compression: Compression) -> Literal["r|gz", "r|*"]:
    return "r|gz" if compression == "gz" else "r|*"


def _indexed_mode(compression: Compression) -> Literal["r:gz", "r:*"]:
    return "r:gz" if compression == "gz" else "r:*"
