#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import tarfile
import uuid
from pathlib import Path

import pytest

from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import (
    create_tar,
)
from cmk.relay_protocols.configuration import CONFIG_ARCHIVE_ROOT_FOLDER_NAME as ROOT


@pytest.fixture
def common_parent(tmp_path: Path) -> Path:
    result = Path(tmp_path) / str(uuid.uuid4())
    result.mkdir(parents=True, exist_ok=True)
    return result


def test_create_tar_with_single_file(common_parent: Path) -> None:
    """Test creating tar archive with a single file."""
    # Create test file
    test_file = common_parent / "test.txt"
    test_content = "Hello, World!"
    test_file.write_text(test_content)

    # Create tar archive
    result = create_tar(common_parent)

    assert isinstance(result, bytes)
    assert len(result) > 0

    # verify tar contents
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        assert len(tar.getmembers()) == 2

        assert tar.getmember(ROOT).isdir()

        member = tar.getmember(f"{ROOT}/test.txt")

        # Verify file content
        file_obj = tar.extractfile(member)
        assert file_obj is not None
        content = file_obj.read().decode("utf-8")
        assert content == test_content


def test_create_tar_with_symlink(common_parent: Path) -> None:
    """Test creating tar archive with a symlink in it."""
    # Create destination file and link to it
    test_file_dst = common_parent / ".." / "text.txt"
    test_content = "Hello, World!"
    test_file_dst.write_text(test_content)
    test_file = common_parent / "link.txt"
    test_file.symlink_to("../text.txt")

    # Create tar archive
    result = create_tar(common_parent)

    # verify tar contents
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        assert len(tar.getmembers()) == 2

        assert tar.getmember(ROOT).isdir()

        member = tar.getmember(f"{ROOT}/link.txt")
        assert member.issym()
        assert member.linkname == "../text.txt"


def test_create_tar_with_multiple_files(common_parent: Path) -> None:
    """Test creating tar archive with multiple files."""
    # Create test files
    file1 = common_parent / "file1.txt"
    file2 = common_parent / "file2.txt"
    file1.write_text("Content 1")
    file2.write_text("Content 2")

    # Create tar archive
    result = create_tar(common_parent)

    # Verify tar content
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        assert len(tar.getmembers()) == 3
        names = {m.name for m in members}
        assert len(names) == len(members)
        assert names == {ROOT, f"{ROOT}/file1.txt", f"{ROOT}/file2.txt"}


def test_create_tar_with_directory_structure(common_parent: Path) -> None:
    """Test creating tar archive preserving directory structure."""
    # Create directory structure
    subdir1 = common_parent / "dir1"
    subdir2 = common_parent / "dir2" / "subdir"
    subdir1.mkdir()
    subdir2.mkdir(parents=True)

    file1 = subdir1 / "file1.txt"
    file2 = subdir2 / "file2.txt"
    file3 = common_parent / "root_file.txt"

    file1.write_text("Content 1")
    file2.write_text("Content 2")
    file3.write_text("Root content")

    # Create tar archive
    result = create_tar(common_parent)

    # Verify tar contents preserve structure
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        names = {m.name for m in members}
        assert f"{ROOT}/dir1/file1.txt" in names
        assert f"{ROOT}/dir2/subdir/file2.txt" in names
        assert f"{ROOT}/root_file.txt" in names


def test_create_tar_with_nested_common_parent(common_parent: Path) -> None:
    """Test with files in subdirectories using a nested common parent."""
    # Create directory structure
    parent = common_parent / "parent"
    subdir = parent / "subdir"
    subdir.mkdir(parents=True)

    file1 = parent / "file1.txt"
    file2 = subdir / "file2.txt"
    file1.write_text("File 1")
    file2.write_text("File 2")

    # Create tar with parent as common parent
    result = create_tar(common_parent)

    # Verify relative paths from parent
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        names = {m.name for m in members}
        assert len(names) == len(members)
        assert names == {
            ROOT,
            f"{ROOT}/parent",
            f"{ROOT}/parent/file1.txt",
            f"{ROOT}/parent/subdir",
            f"{ROOT}/parent/subdir/file2.txt",
        }


def test_create_tar_with_binary_file(common_parent: Path) -> None:
    """Test creating tar archive with binary file."""
    # Create binary file
    binary_file = common_parent / "binary.bin"
    binary_content = b"\x00\x01\x02\x03\xff\xfe\xfd"
    binary_file.write_bytes(binary_content)

    # Create tar archive
    result = create_tar(common_parent)

    # Verify binary content is preserved
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        member = tar.getmember(f"{ROOT}/binary.bin")
        file_obj = tar.extractfile(member)
        assert file_obj is not None
        content = file_obj.read()
        assert content == binary_content


def test_create_tar_with_unicode_content(common_parent: Path) -> None:
    """Test creating tar archive with unicode content."""
    unicode_file = common_parent / "unicode.txt"
    unicode_content = "Hello 世界! 🌍 Ñoño"
    unicode_file.write_text(unicode_content, encoding="utf-8")

    # Create tar archive
    result = create_tar(common_parent)

    # Verify unicode content is preserved
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        file_obj = tar.extractfile(tar.getmember(f"{ROOT}/unicode.txt"))
        assert file_obj is not None
        content = file_obj.read().decode("utf-8")
        assert content == unicode_content


def test_create_tar_is_uncompressed(common_parent: Path) -> None:
    """Test that created tar archive is uncompressed."""
    test_file = common_parent / "test.txt"
    test_file.write_text("test content")

    # Create tar archive
    result = create_tar(common_parent)

    # Verify tar is uncompressed (mode 'r' should work, not 'r:gz' or 'r:bz2')
    tar_buffer = io.BytesIO(result)

    # Should open without specifying compression
    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        assert len(tar.getmembers()) == 2


def test_create_tar_with_deeply_nested_structure(common_parent: Path) -> None:
    """Test creating tar archive with deeply nested directory structure."""
    # Create deeply nested structure
    deep_dir = common_parent / "level1" / "level2" / "level3" / "level4" / "level5"
    deep_dir.mkdir(parents=True)

    deep_file = deep_dir / "deep_file.txt"
    deep_file.write_text("deeply nested content")

    # Create tar archive
    result = create_tar(common_parent)

    # Verify structure is preserved
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        names = {m.name for m in members}
        assert len(names) == len(members)
        assert names == {
            ROOT,
            f"{ROOT}/level1",
            f"{ROOT}/level1/level2",
            f"{ROOT}/level1/level2/level3",
            f"{ROOT}/level1/level2/level3/level4",
            f"{ROOT}/level1/level2/level3/level4/level5",
            f"{ROOT}/level1/level2/level3/level4/level5/deep_file.txt",
        }


def test_create_tar_with_mixed_file_types(common_parent: Path) -> None:
    """Test creating tar archive with various file types mixed."""
    # Create different types of files
    text_file = common_parent / "text.txt"
    binary_file = common_parent / "binary.bin"
    empty_file = common_parent / "empty.dat"

    text_file.write_text("text content")
    binary_file.write_bytes(b"\x00\xff\x00\xff")
    empty_file.touch()

    # Create tar archive with all files
    result = create_tar(common_parent)

    # Verify all files are included
    tar_buffer = io.BytesIO(result)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        names = {m.name for m in tar.getmembers()}
        assert names == {ROOT, f"{ROOT}/binary.bin", f"{ROOT}/empty.dat", f"{ROOT}/text.txt"}
