#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import io
import math
import tarfile
from collections.abc import Callable, Iterator
from contextlib import _GeneratorContextManager, contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any, Final, IO, Literal, TypedDict, Unpack


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
    else:
        return f"{value:.2f} {display_unit}"


class NotAValidArchive(ValueError): ...


class UnpackedArchiveTooLargeError(ValueError): ...


class SecurityViolation(ValueError): ...


class ZipArchiveTooLarge(ValueError):
    def __init__(self, size_in_bytes: int):
        self.size_in_bytes: Final = size_in_bytes


TarFilterCallable = Callable[[tarfile.TarInfo, str], tarfile.TarInfo | None]
FilterType = Literal["fully_trusted", "tar", "data"] | TarFilterCallable


class BaseSafeTarFile:
    """Base wrapper for TarFile with enforced security checks."""

    def __init__(self, tar: tarfile.TarFile, archive: "CheckmkTarArchive"):
        self._tar = tar
        self._archive = archive
        self._member_iter = iter(self._tar)

    def __iter__(self) -> Iterator[tarfile.TarInfo]:
        return self

    def __next__(self) -> tarfile.TarInfo:
        return next(self._member_iter)

    def extract(
        self, member: tarfile.TarInfo | str, path: str | Path = ".", _filter: FilterType = "data"
    ) -> None:
        """
        Safely extract an archive to the desired path.
        """
        path = Path(path).resolve()
        member_name = member.name if isinstance(member, tarfile.TarInfo) else member
        resolved = (path / member_name).resolve()
        if not resolved.is_relative_to(path):
            raise SecurityViolation(f"Path traversal attempt: {member_name}")
        self._tar.extract(member, path=path, filter=_filter)

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

    def __getattr__(self, name: str) -> Any:
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
    Validates incrementally during iteration."""

    def __init__(self, tar: tarfile.TarFile, archive: "CheckmkTarArchive"):
        super().__init__(tar, archive)
        self._total_size = 0
        self._file_count = 0

    def __next__(self) -> tarfile.TarInfo:
        # Get next member from underlying tar
        member = next(self._member_iter)
        self._file_count += 1
        if self._file_count > self._archive.file_limit:
            raise UnpackedArchiveTooLargeError(
                f"Archive contains too many files ({self._file_count})"
            )

        self._total_size += member.size
        if self._total_size > self._archive.size_limit_bytes:
            raise UnpackedArchiveTooLargeError(
                f"Archive exceeds total size limit: "
                f"({fmt_bytes(self._total_size)} > {fmt_bytes(self._archive.size_limit_bytes)})"
            )

        self._archive.validate_member(member)
        return member

    def getmembers(self) -> None:
        raise TypeError("getmembers() not supported in streaming-safe mode; use iteration instead")


class SafeIndexedTarFile(BaseSafeTarFile):
    """Safe wrapper around TarFile in indexed mode (r:gz).
    Validates all members eagerly on open."""

    def __init__(self, tar: tarfile.TarFile, archive: "CheckmkTarArchive") -> None:
        super().__init__(tar, archive)
        members = tar.getmembers()

        if len(members) > archive.file_limit:
            raise UnpackedArchiveTooLargeError(f"Archive contains too many files ({len(members)})")

        total_size = sum(m.size for m in members)
        if total_size > archive.size_limit_bytes:
            raise UnpackedArchiveTooLargeError(
                f"Archive exceeds total size limit: "
                f"({fmt_bytes(total_size)} > {fmt_bytes(archive.size_limit_bytes)})"
            )

        for m in members:
            archive.validate_member(m)
        self._member_iter = iter(members)


class _ArchiveSettings(TypedDict, total=False):
    size_limit_bytes: int
    file_limit: int
    per_file_limit: int
    compression: Literal["gz", "*"]
    allow_symlinks: bool


class CheckmkTarArchive:
    RAW_MAX_SIZE_LIMIT_BYTES: Final[int] = 100 * 1024 * 1024  # 100 MB
    ARCHIVE_MAX_SIZE_LIMIT_BYTES: Final[int] = 200 * 1024 * 1024  # 200 MB
    ARCHIVE_MAX_SIZE_LIMIT_BYTES_PER_FILE: Final[int] = 50 * 1024 * 1024  # 50 MB
    ARCHIVE_MAX_TOTAL_FILES: Final[int] = 10_000

    def __init__(
        self,
        size_limit_bytes: int = ARCHIVE_MAX_SIZE_LIMIT_BYTES,
        file_limit: int = ARCHIVE_MAX_TOTAL_FILES,
        per_file_limit: int = ARCHIVE_MAX_SIZE_LIMIT_BYTES_PER_FILE,
        compression: Literal["gz", "*"] = "gz",
        allow_symlinks: bool = False,
    ):
        self.size_limit_bytes = size_limit_bytes
        self.file_limit = file_limit
        self.per_file_limit = per_file_limit
        self.compression = compression
        self.READ_MODE_STREAM = f"r|{compression}"  # streaming, safe extraction, validation
        self.READ_MODE_INDEX = (
            f"r:{compression}"  # full in memory, pre-scan, safe extraction, validation
        )
        self.allow_symlinks = allow_symlinks

    def validate_member(self, member: tarfile.TarInfo) -> None:
        """Validate a single tar member."""
        if member.name == "":
            # This should never happen
            raise NotAValidArchive("Archive member name is cannot be empty")
        if not self.allow_symlinks:
            if member.islnk() or member.issym():
                raise SecurityViolation(f"Symlink or hardlink not allowed: {member.name}")
        if member.ischr() or member.isblk() or member.isfifo():
            raise SecurityViolation(f"Special file not allowed: {member.name}")

        if member.size > self.per_file_limit:
            raise UnpackedArchiveTooLargeError(
                f"File {member.name} exceeds per-file size limit: ({fmt_bytes(member.size)} > {fmt_bytes(self.per_file_limit)})"
            )

    @contextmanager
    def open_buffer(
        self,
        buffer: IO[bytes],
        streaming: bool = True,
    ) -> Iterator[SafeStreamedTarFile | SafeIndexedTarFile]:
        mode: str = self.READ_MODE_STREAM if streaming else self.READ_MODE_INDEX
        try:
            self._check_compressed_size(buffer)
            buffer.seek(0)
            tar = tarfile.open(fileobj=buffer, mode=mode)  # type: ignore[call-overload]
            with tar:
                if streaming:
                    yield SafeStreamedTarFile(tar, self)
                else:
                    yield SafeIndexedTarFile(tar, self)

        except tarfile.ReadError as exc:
            raise NotAValidArchive() from exc

    @contextmanager
    def open_path(
        self,
        path: Path,
        streaming: bool = True,
    ) -> Iterator[SafeIndexedTarFile | SafeStreamedTarFile]:
        mode: str = self.READ_MODE_STREAM if streaming else self.READ_MODE_INDEX
        try:
            self._check_compressed_size(path)
            tar = tarfile.open(name=path, mode=mode)  # type: ignore[call-overload]
            with tar:
                if streaming:
                    yield SafeStreamedTarFile(tar, self)
                else:
                    yield SafeIndexedTarFile(tar, self)
        except tarfile.ReadError as exc:
            raise NotAValidArchive() from exc

    def _check_compressed_size(self, source: IO[bytes] | Path | str) -> None:
        """
        Check compressed archive size for a file-like object or a file path.
        """
        if isinstance(source, str | Path):
            path = Path(source)
            size = path.stat().st_size
        else:
            current_pos = source.tell()
            source.seek(0, 2)
            size = source.tell()
            source.seek(current_pos)

        if size > self.RAW_MAX_SIZE_LIMIT_BYTES:
            raise UnpackedArchiveTooLargeError(
                f"Compressed archive too large: "
                f"({fmt_bytes(size)} > {fmt_bytes(self.RAW_MAX_SIZE_LIMIT_BYTES)})"
            )

    @classmethod
    def from_bytes(
        cls, raw: bytes, streaming: bool = True, **kwargs: Unpack[_ArchiveSettings]
    ) -> _GeneratorContextManager[SafeIndexedTarFile | SafeStreamedTarFile]:
        buffer = io.BytesIO(raw)
        return cls(**kwargs).open_buffer(buffer, streaming=streaming)

    @classmethod
    def from_buffer(
        cls, buffer: IO[bytes], streaming: bool = True, **kwargs: Unpack[_ArchiveSettings]
    ) -> _GeneratorContextManager[SafeIndexedTarFile | SafeStreamedTarFile]:
        return cls(**kwargs).open_buffer(buffer, streaming=streaming)

    @classmethod
    def from_path(
        cls, path: Path, streaming: bool = True, **kwargs: Unpack[_ArchiveSettings]
    ) -> _GeneratorContextManager[SafeIndexedTarFile | SafeStreamedTarFile]:
        return cls(**kwargs).open_path(path, streaming=streaming)

    @classmethod
    def validate_bytes(cls, raw: bytes, **kwargs: Unpack[_ArchiveSettings]) -> None:
        """Validate archive without writing anything to disk."""
        with cls.from_bytes(raw, **kwargs) as archive:
            for _ in archive:
                ...
