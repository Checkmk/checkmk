#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import tarfile
from collections.abc import Iterable
from pathlib import Path

import pytest

from cmk.ccc.tar_archive import (
    ArchiveLimits,
    NotAValidArchive,
    open_buffer_indexed,
    open_buffer_streaming,
    open_bytes_indexed,
    open_bytes_streaming,
    open_path_indexed,
    open_path_streaming,
    SecurityViolation,
    UnpackedArchiveTooLargeError,
    validate_bytes,
)


def make_tarfile_io(files: Iterable[tuple[str, bytes]]) -> io.BytesIO:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files:
            tarinfo = tarfile.TarInfo(name)
            tarinfo.size = len(content)
            tar.addfile(tarinfo, io.BytesIO(content))
    buf.seek(0)
    return buf


def make_tarfile_bytes(files: Iterable[tuple[str, bytes]]) -> bytes:
    return make_tarfile_io(files).getvalue()


def make_tarfile_path(
    files: Iterable[tuple[str, bytes]],
    tmp_path: Path,
) -> Path:
    tar_path = tmp_path / "archive.tar.gz"
    tar_path.write_bytes(make_tarfile_io(files).getvalue())
    return tar_path


def make_tarfile_bytes_from_members(*members: tarfile.TarInfo) -> bytes:
    """Build an archive from members that carry no content, such as directories or device files."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for member in members:
            tar.addfile(member)
    return buf.getvalue()


def make_member(name: str, member_type: bytes) -> tarfile.TarInfo:
    member = tarfile.TarInfo(name)
    member.type = member_type
    return member


LINK_TARGET_CONTENT = b"target content"


def make_tarfile_bytes_with_links() -> bytes:
    """Build an archive holding every kind of link next to a directory and the link target."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        target = tarfile.TarInfo("target.txt")
        target.size = len(LINK_TARGET_CONTENT)
        tar.addfile(target, io.BytesIO(LINK_TARGET_CONTENT))

        for name, member_type, linkname in [
            ("symlink.txt", tarfile.SYMTYPE, "target.txt"),
            ("hardlink.txt", tarfile.LNKTYPE, "target.txt"),
            ("dangling.txt", tarfile.SYMTYPE, "nowhere.txt"),
        ]:
            member = make_member(name, member_type)
            member.linkname = linkname
            tar.addfile(member)

        tar.addfile(make_member("subdir", tarfile.DIRTYPE))
    return buf.getvalue()


def test_safe_extractall_streaming_bytes(tmp_path: Path) -> None:
    files = [("a.txt", b"hello"), ("b.txt", b"world")]
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with open_bytes_streaming(raw) as safe_tar:
        safe_tar.extractall(dest)

    for f, content in files:
        assert (dest / f).read_bytes() == content


def test_safe_extractall_streaming_buffer(tmp_path: Path) -> None:
    files = [("a.txt", b"hello"), ("b.txt", b"world")]
    buf = make_tarfile_io(files)
    dest = tmp_path / "dest"

    with open_buffer_streaming(buf) as safe_tar:
        safe_tar.extractall(dest)

    for f, content in files:
        assert (dest / f).read_bytes() == content


def test_safe_extractall_streaming_path(tmp_path: Path) -> None:
    files = [("a.txt", b"hello"), ("b.txt", b"world")]
    path = make_tarfile_path(files, tmp_path)
    dest = tmp_path / "dest"

    with open_path_streaming(path) as safe_tar:
        safe_tar.extractall(dest)

    for f, content in files:
        assert (dest / f).read_bytes() == content


def test_safe_extract_indexed_bytes(tmp_path: Path) -> None:
    files = [("a.txt", b"hello"), ("b.txt", b"world")]
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with open_bytes_indexed(raw) as safe_tar:
        assert [m.name for m in safe_tar.getmembers()] == ["a.txt", "b.txt"]
        for member in safe_tar.getmembers():
            safe_tar.extract(member, dest)

    for f, content in files:
        assert (dest / f).read_bytes() == content


def test_safe_extract_indexed_buffer(tmp_path: Path) -> None:
    files = [("a.txt", b"hello"), ("b.txt", b"world")]
    buf = make_tarfile_io(files)
    dest = tmp_path / "dest"

    with open_buffer_indexed(buf) as safe_tar:
        for member in safe_tar.getmembers():
            safe_tar.extract(member, dest)

    for f, content in files:
        assert (dest / f).read_bytes() == content


def test_safe_extract_indexed_path(tmp_path: Path) -> None:
    files = [("a.txt", b"hello"), ("b.txt", b"world")]
    path = make_tarfile_path(files, tmp_path)
    dest = tmp_path / "dest"

    with open_path_indexed(path) as safe_tar:
        for member in safe_tar.getmembers():
            safe_tar.extract(member, dest)

    for f, content in files:
        assert (dest / f).read_bytes() == content


def test_invalid_archive() -> None:
    with pytest.raises(NotAValidArchive):
        validate_bytes(b"not a tar")


@pytest.mark.parametrize(
    "files, limits",
    [
        pytest.param(
            [("a.txt", b"x"), ("b.txt", b"x"), ("c.txt", b"x")],
            ArchiveLimits(file_limit=2),
            id="file count",
        ),
        pytest.param(
            [("big.txt", b"xx")],
            ArchiveLimits(per_file_limit=1),
            id="per-file size",
        ),
        pytest.param(
            [("a.txt", b"x"), ("b.txt", b"x")],
            ArchiveLimits(size_limit_bytes=1),
            id="total size",
        ),
    ],
)
def test_indexed_validates_eagerly_on_open(
    files: Iterable[tuple[str, bytes]], limits: ArchiveLimits
) -> None:
    """In contrast to streaming mode, indexed mode validates before the caller iterates."""
    raw = make_tarfile_bytes(files)

    with pytest.raises(UnpackedArchiveTooLargeError), open_bytes_indexed(raw, limits=limits):
        pytest.fail("indexed mode must reject the archive before the context body runs")


def test_validate_bytes_enforces_the_limits() -> None:
    """Validation streams through every member, so the limits apply although nothing is written."""
    raw = make_tarfile_bytes([("a.txt", b"x"), ("b.txt", b"x"), ("c.txt", b"x")])

    with pytest.raises(UnpackedArchiveTooLargeError):
        validate_bytes(raw, limits=ArchiveLimits(file_limit=2))


def test_per_file_size_limit_bytes(tmp_path: Path) -> None:
    max_size = 100
    files = [("big.txt", b"x" * (max_size + 1))]
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with (
        pytest.raises(UnpackedArchiveTooLargeError),
        open_bytes_streaming(raw, limits=ArchiveLimits(per_file_limit=max_size)) as safe_tar,
    ):
        safe_tar.extractall(dest)


def test_total_file_limit_bytes(tmp_path: Path) -> None:
    files = [("a.txt", b"x"), ("b.txt", b"x"), ("c.txt", b"x")]
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with (
        pytest.raises(UnpackedArchiveTooLargeError),
        open_bytes_streaming(raw, limits=ArchiveLimits(file_limit=2)) as safe_tar,
    ):
        safe_tar.extractall(dest)


def test_compressed_size_limit_bytes() -> None:
    """The compressed size is checked before the archive is opened, so nothing is read at all."""
    raw = make_tarfile_bytes([("a.txt", b"hello")])

    with (
        pytest.raises(UnpackedArchiveTooLargeError),
        open_bytes_streaming(raw, limits=ArchiveLimits(raw_limit_bytes=len(raw) - 1)),
    ):
        pytest.fail("an oversized archive must be rejected before the context body runs")


def test_compressed_size_limit_path(tmp_path: Path) -> None:
    path = make_tarfile_path([("a.txt", b"hello")], tmp_path)

    with (
        pytest.raises(UnpackedArchiveTooLargeError),
        open_path_streaming(path, limits=ArchiveLimits(raw_limit_bytes=path.stat().st_size - 1)),
    ):
        pytest.fail("an oversized archive must be rejected before the context body runs")


def test_indexed_extract_rejects_path_traversal(tmp_path: Path) -> None:
    raw = make_tarfile_bytes([("../evil.txt", b"malicious")])

    with pytest.raises(SecurityViolation), open_bytes_indexed(raw) as safe_tar:
        safe_tar.extract(safe_tar.getmembers()[0], tmp_path / "dest")


def test_path_traversal_bytes(tmp_path: Path) -> None:
    files = [("../evil.txt", b"malicious")]
    raw = make_tarfile_bytes(files)
    dest = tmp_path / "dest"

    with pytest.raises(SecurityViolation), open_bytes_streaming(raw) as safe_tar:
        safe_tar.extractall(dest)


@pytest.mark.parametrize(
    "member_type",
    [tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE],
    ids=["character device", "block device", "fifo"],
)
def test_special_file_blocked(member_type: bytes) -> None:
    """Special files are refused whatever the limits permit."""
    raw = make_tarfile_bytes_from_members(make_member("special", member_type))

    with pytest.raises(SecurityViolation):
        validate_bytes(raw)


def test_hardlink_blocked() -> None:
    member = make_member("hard.txt", tarfile.LNKTYPE)
    member.linkname = "a.txt"
    raw = make_tarfile_bytes_from_members(member)

    with pytest.raises(SecurityViolation):
        validate_bytes(raw, limits=ArchiveLimits(allow_symlinks=False))


def test_empty_member_name_rejected() -> None:
    with pytest.raises(NotAValidArchive):
        validate_bytes(make_tarfile_bytes_from_members(tarfile.TarInfo("")))


def test_symlink_blocked(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tarinfo = tarfile.TarInfo("link.txt")
        tarinfo.type = tarfile.SYMTYPE
        tar.addfile(tarinfo)
    buf.seek(0)

    dest = tmp_path / "dest"
    with (
        pytest.raises(SecurityViolation),
        open_buffer_streaming(buf, limits=ArchiveLimits(allow_symlinks=False)) as safe_tar,
    ):
        safe_tar.extractall(dest)


def test_symlink_allowed(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tarinfo = tarfile.TarInfo("link.txt")
        tarinfo.type = tarfile.SYMTYPE
        tar.addfile(tarinfo)
    buf.seek(0)

    dest = tmp_path / "dest"
    with open_buffer_streaming(buf, limits=ArchiveLimits(allow_symlinks=True)) as safe_tar:
        safe_tar.extractall(dest)


def test_name_is_the_source_path(tmp_path: Path) -> None:
    path = make_tarfile_path([("a.txt", b"hello")], tmp_path)

    with open_path_streaming(path) as safe_tar:
        assert safe_tar.name == str(path)


def test_name_is_none_without_source_path() -> None:
    with open_bytes_streaming(make_tarfile_bytes([("a.txt", b"hello")])) as safe_tar:
        assert safe_tar.name is None


def test_iteration_bytes() -> None:
    files = [(f"file{i}.txt", f"data{i}".encode()) for i in range(5)]
    raw = make_tarfile_bytes(files)

    with open_bytes_streaming(
        raw, compression="*", limits=ArchiveLimits(allow_symlinks=False)
    ) as safe_tar:
        first = next(safe_tar)
        assert first.name.startswith("file")

        remaining_names = [m.name for m in safe_tar]
        expected = [f"file{i}.txt" for i in range(1, 5)]
        assert remaining_names == expected

        with pytest.raises(StopIteration):
            next(safe_tar)


def test_extractfile_by_name() -> None:
    files = {"file0.txt": b"hello", "file1.txt": b"world"}
    raw = make_tarfile_bytes(files.items())

    with open_bytes_streaming(
        raw, compression="*", limits=ArchiveLimits(allow_symlinks=False)
    ) as safe_tar:
        f = safe_tar.extractfile_by_name("file1.txt")
        assert f is not None
        assert f.read() == files["file1.txt"]

        f2 = safe_tar.extractfile_by_name("notfound")
        assert f2 is None


def test_streaming_extractall_skips_consumed_members(tmp_path: Path) -> None:
    """The cursor cannot go back, so extractall only ever sees what iteration has not consumed."""
    files = {"a.txt": b"hello", "b.txt": b"world"}
    dest = tmp_path / "dest"

    with open_bytes_streaming(make_tarfile_bytes(files.items())) as safe_tar:
        next(safe_tar)
        safe_tar.extractall(dest)

    assert not (dest / "a.txt").exists()
    assert (dest / "b.txt").read_bytes() == files["b.txt"]


def test_extractfile_by_name_without_a_name_keeps_the_cursor() -> None:
    """The empty name is answered without searching, so the streamed members stay reachable."""
    with open_bytes_streaming(make_tarfile_bytes([("a.txt", b"hello")])) as safe_tar:
        assert safe_tar.extractfile_by_name("") is None
        assert [m.name for m in safe_tar] == ["a.txt"]


def test_extractfile_by_name_returns_none_for_a_directory() -> None:
    raw = make_tarfile_bytes_from_members(make_member("subdir", tarfile.DIRTYPE))

    with open_bytes_streaming(raw) as safe_tar:
        assert safe_tar.extractfile_by_name("subdir") is None


@pytest.mark.parametrize(
    "member_name, expected_payload",
    [
        ("target.txt", LINK_TARGET_CONTENT),
        ("symlink.txt", None),
        ("hardlink.txt", None),
        ("dangling.txt", None),
        ("subdir", None),
    ],
    ids=["link target", "symlink", "hardlink", "dangling symlink", "directory"],
)
def test_extractfile_by_name_payload(member_name: str, expected_payload: bytes | None) -> None:
    """Only a regular file has a payload; reaching a link does not raise a StreamError."""
    with open_bytes_streaming(make_tarfile_bytes_with_links()) as safe_tar:
        obj = safe_tar.extractfile_by_name(member_name)
        assert (None if obj is None else obj.read()) == expected_payload


def test_indexed_extract_single_member(tmp_path: Path) -> None:
    files = {"a.txt": b"hello", "b.txt": b"world"}
    raw = make_tarfile_bytes(files.items())
    dest = tmp_path / "dest"

    with open_bytes_indexed(raw) as safe_tar:
        safe_tar.extract(safe_tar.getmembers()[1], dest)

    assert (dest / "b.txt").read_bytes() == files["b.txt"]
    assert not (dest / "a.txt").exists()


def test_indexed_extract_in_reverse_archive_order(tmp_path: Path) -> None:
    """Members stay accessible in any order, in contrast to streaming mode."""
    files = [("a.txt", b"hello"), ("b.txt", b"world")]
    dest = tmp_path / "dest"

    with open_bytes_indexed(make_tarfile_bytes(files)) as safe_tar:
        for member in reversed(safe_tar.getmembers()):
            safe_tar.extract(member, dest)

    for f, content in files:
        assert (dest / f).read_bytes() == content
