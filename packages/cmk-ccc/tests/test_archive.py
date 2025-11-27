#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# nosec B202

import io
import tarfile
from pathlib import Path

import pytest

from cmk.ccc.archive import (
    CheckmkTarArchive,
    NotAValidArchive,
    SecurityViolation,
    UnpackedArchiveTooLargeError,
)


def make_tarfile_io(
    files: dict[str, bytes],
    compress: bool = True,
) -> io.BytesIO:
    mode = "w:gz" if compress else "w"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode=mode) as tar:  # type: ignore[call-overload]
        for name, content in files.items():
            tarinfo = tarfile.TarInfo(name)
            tarinfo.size = len(content)
            tar.addfile(tarinfo, io.BytesIO(content))
    buf.seek(0)
    return buf


def make_tarfile_bytes(files: dict[str, bytes], compress: bool = True) -> bytes:
    return make_tarfile_io(files, compress).getvalue()


def make_tarfile_path(
    files: dict[str, bytes],
    tmp_path: Path,
    compress: bool = True,
) -> Path:
    tar_path = tmp_path / "archive.tar.gz"
    tar_path.write_bytes(make_tarfile_io(files, compress).getvalue())
    return tar_path


def test_safe_extractall_basic_bytes(tmp_path: Path) -> None:
    files = {"a.txt": b"hello", "b.txt": b"world"}
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with CheckmkTarArchive.from_bytes(raw) as safe_tar:
        safe_tar.extractall(dest)  # nosec B202

    for f, content in files.items():
        assert (dest / f).read_bytes() == content


def test_safe_extractall_basic_io(tmp_path: Path) -> None:
    files = {"a.txt": b"hello", "b.txt": b"world"}
    buf = make_tarfile_io(files)
    dest = tmp_path / "dest"

    with CheckmkTarArchive.from_buffer(buf) as safe_tar:
        safe_tar.extractall(dest)  # nosec B202

    for f, content in files.items():
        assert (dest / f).read_bytes() == content


def test_safe_extractall_basic_path(tmp_path: Path) -> None:
    files = {"a.txt": b"hello", "b.txt": b"world"}
    path = make_tarfile_path(files, tmp_path)
    dest = tmp_path / "dest"

    with CheckmkTarArchive.from_path(path) as safe_tar:
        safe_tar.extractall(dest)  # nosec B202

    for f, content in files.items():
        assert (dest / f).read_bytes() == content


def test_path_traversal_bytes(tmp_path: Path) -> None:
    files = {"../evil.txt": b"malicious"}
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with pytest.raises(SecurityViolation):
        with CheckmkTarArchive.from_bytes(raw) as safe_tar:
            safe_tar.extractall(dest)  # nosec B202


def test_per_file_size_limit_bytes(tmp_path: Path) -> None:
    max_size = 100
    files = {"big.txt": b"x" * (max_size + 1)}
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with pytest.raises(UnpackedArchiveTooLargeError):
        with CheckmkTarArchive.from_bytes(raw, per_file_limit=max_size) as safe_tar:
            safe_tar.extractall(dest)  # nosec B202


def test_total_file_limit_bytes(tmp_path: Path) -> None:
    files = {"a.txt": b"x", "b.txt": b"x", "c.txt": b"x"}
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with pytest.raises(UnpackedArchiveTooLargeError):
        with CheckmkTarArchive.from_bytes(raw, file_limit=2) as safe_tar:
            safe_tar.extractall(dest)  # nosec B202


def test_iteration_bytes() -> None:
    files = {f"file{i}.txt": f"data{i}".encode() for i in range(5)}
    raw = make_tarfile_bytes(files)

    with CheckmkTarArchive.from_bytes(raw, compression="*", allow_symlinks=False) as safe_tar:
        first = next(safe_tar)
        assert first.name.startswith("file")

        remaining_names = [m.name for m in safe_tar]
        expected = [f"file{i}.txt" for i in range(1, 5)]
        assert remaining_names == expected

        with pytest.raises(StopIteration):
            next(safe_tar)


def test_safe_extractfile_bytes() -> None:
    files = {"file0.txt": b"hello", "file1.txt": b"world"}
    raw = make_tarfile_bytes(files)

    with CheckmkTarArchive.from_bytes(raw, compression="*", allow_symlinks=False) as safe_tar:
        f = safe_tar.extractfile_by_name("file1.txt")
        assert f is not None
        assert f.read() == files["file1.txt"]

        f2 = safe_tar.extractfile_by_name("notfound")
        assert f2 is None


def test_invalid_archive() -> None:
    with pytest.raises(NotAValidArchive):
        CheckmkTarArchive.validate_bytes(b"not a tar")


def test_symlink_blocked(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tarinfo = tarfile.TarInfo("link.txt")
        tarinfo.type = tarfile.SYMTYPE
        tar.addfile(tarinfo)
    buf.seek(0)

    dest = tmp_path / "dest"
    with pytest.raises(SecurityViolation):
        with CheckmkTarArchive.from_buffer(buf, allow_symlinks=False) as safe_tar:
            safe_tar.extractall(
                dest,
            )  # nosec B202


def test_symlink_allowed(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tarinfo = tarfile.TarInfo("link.txt")
        tarinfo.type = tarfile.SYMTYPE
        tar.addfile(tarinfo)
    buf.seek(0)

    dest = tmp_path / "dest"
    with CheckmkTarArchive.from_buffer(buf, allow_symlinks=True) as safe_tar:
        safe_tar.extractall(dest)  # nosec B202
