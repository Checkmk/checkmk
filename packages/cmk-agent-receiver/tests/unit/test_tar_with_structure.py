#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import io
import tarfile
from pathlib import Path

import pytest

from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import (
    create_tar_with_structure_as_base64,
)


def test_create_tar_with_single_file(tmp_path: Path) -> None:
    """Test creating tar archive with a single file."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_content = "Hello, World!"
    test_file.write_text(test_content)

    # Create tar archive
    result = create_tar_with_structure_as_base64([test_file], tmp_path)

    # Verify result is base64 string
    assert isinstance(result, str)
    assert len(result) > 0

    # Decode and verify tar contents
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        assert len(members) == 1
        assert members[0].name == "test.txt"

        # Verify file content
        file_obj = tar.extractfile(members[0])
        assert file_obj is not None
        content = file_obj.read().decode("utf-8")
        assert content == test_content


def test_create_tar_with_multiple_files(tmp_path: Path) -> None:
    """Test creating tar archive with multiple files."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("Content 1")
    file2.write_text("Content 2")

    # Create tar archive
    result = create_tar_with_structure_as_base64([file1, file2], tmp_path)

    # Verify tar contents
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        assert len(members) == 2
        names = sorted([m.name for m in members])
        assert names == ["file1.txt", "file2.txt"]


def test_create_tar_with_directory_structure(tmp_path: Path) -> None:
    """Test creating tar archive preserving directory structure."""
    # Create directory structure
    subdir1 = tmp_path / "dir1"
    subdir2 = tmp_path / "dir2" / "subdir"
    subdir1.mkdir()
    subdir2.mkdir(parents=True)

    file1 = subdir1 / "file1.txt"
    file2 = subdir2 / "file2.txt"
    file3 = tmp_path / "root_file.txt"

    file1.write_text("Content 1")
    file2.write_text("Content 2")
    file3.write_text("Root content")

    # Create tar archive
    result = create_tar_with_structure_as_base64([file1, file2, file3], tmp_path)

    # Verify tar contents preserve structure
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        names = sorted([m.name for m in members])
        assert "dir1/file1.txt" in names
        assert "dir2/subdir/file2.txt" in names
        assert "root_file.txt" in names


def test_create_tar_with_nested_common_parent(tmp_path: Path) -> None:
    """Test with files in subdirectories using a nested common parent."""
    # Create directory structure
    parent = tmp_path / "parent"
    subdir = parent / "subdir"
    subdir.mkdir(parents=True)

    file1 = parent / "file1.txt"
    file2 = subdir / "file2.txt"
    file1.write_text("File 1")
    file2.write_text("File 2")

    # Create tar with parent as common parent
    result = create_tar_with_structure_as_base64([file1, file2], parent)

    # Verify relative paths from parent
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        names = sorted([m.name for m in members])
        assert names == ["file1.txt", "subdir/file2.txt"]


def test_create_tar_empty_file_list_raises_error(tmp_path: Path) -> None:
    """Test that empty file list raises ValueError."""
    with pytest.raises(ValueError, match="File list cannot be empty"):
        create_tar_with_structure_as_base64([], Path(tmp_path / "tmp"))


def test_create_tar_nonexistent_file_raises_error(tmp_path: Path) -> None:
    """Test that nonexistent file raises FileNotFoundError."""
    nonexistent_file = tmp_path / "nonexistent.txt"

    with pytest.raises(FileNotFoundError, match="File not found"):
        create_tar_with_structure_as_base64([nonexistent_file], tmp_path)


def test_create_tar_nonexistent_common_parent_raises_error(tmp_path: Path) -> None:
    """Test that nonexistent common parent raises FileNotFoundError."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    nonexistent_parent = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError, match="Common parent directory not found"):
        create_tar_with_structure_as_base64([test_file], nonexistent_parent)


def test_create_tar_file_not_under_common_parent_raises_error(tmp_path: Path) -> None:
    """Test that file not under common parent raises ValueError."""
    # Create file outside common parent
    parent = tmp_path / "parent"
    parent.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside")

    with pytest.raises(ValueError, match="is not under common parent directory"):
        create_tar_with_structure_as_base64([outside_file], parent)


def test_create_tar_with_binary_file(tmp_path: Path) -> None:
    """Test creating tar archive with binary file."""
    # Create binary file
    binary_file = tmp_path / "binary.bin"
    binary_content = b"\x00\x01\x02\x03\xff\xfe\xfd"
    binary_file.write_bytes(binary_content)

    # Create tar archive
    result = create_tar_with_structure_as_base64([binary_file], tmp_path)

    # Verify binary content is preserved
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        assert len(members) == 1
        file_obj = tar.extractfile(members[0])
        assert file_obj is not None
        content = file_obj.read()
        assert content == binary_content


def test_create_tar_with_unicode_content(tmp_path: Path) -> None:
    """Test creating tar archive with unicode content."""
    unicode_file = tmp_path / "unicode.txt"
    unicode_content = "Hello 世界! 🌍 Ñoño"
    unicode_file.write_text(unicode_content, encoding="utf-8")

    # Create tar archive
    result = create_tar_with_structure_as_base64([unicode_file], tmp_path)

    # Verify unicode content is preserved
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        file_obj = tar.extractfile(members[0])
        assert file_obj is not None
        content = file_obj.read().decode("utf-8")
        assert content == unicode_content


def test_create_tar_is_uncompressed(tmp_path: Path) -> None:
    """Test that created tar archive is uncompressed."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Create tar archive
    result = create_tar_with_structure_as_base64([test_file], tmp_path)

    # Verify tar is uncompressed (mode 'r' should work, not 'r:gz' or 'r:bz2')
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    # Should open without specifying compression
    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        assert len(tar.getmembers()) == 1


def test_create_tar_with_deeply_nested_structure(tmp_path: Path) -> None:
    """Test creating tar archive with deeply nested directory structure."""
    # Create deeply nested structure
    deep_dir = tmp_path / "level1" / "level2" / "level3" / "level4" / "level5"
    deep_dir.mkdir(parents=True)

    deep_file = deep_dir / "deep_file.txt"
    deep_file.write_text("deeply nested content")

    # Create tar archive
    result = create_tar_with_structure_as_base64([deep_file], tmp_path)

    # Verify structure is preserved
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        assert len(members) == 1
        assert members[0].name == "level1/level2/level3/level4/level5/deep_file.txt"


def test_create_tar_with_mixed_file_types(tmp_path: Path) -> None:
    """Test creating tar archive with various file types mixed."""
    # Create different types of files
    text_file = tmp_path / "text.txt"
    binary_file = tmp_path / "binary.bin"
    empty_file = tmp_path / "empty.dat"

    text_file.write_text("text content")
    binary_file.write_bytes(b"\x00\xff\x00\xff")
    empty_file.touch()

    # Create tar archive with all files
    result = create_tar_with_structure_as_base64([text_file, binary_file, empty_file], tmp_path)

    # Verify all files are included
    tar_bytes = base64.b64decode(result)
    tar_buffer = io.BytesIO(tar_bytes)

    with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
        members = tar.getmembers()
        names = sorted([m.name for m in members])
        assert names == ["binary.bin", "empty.dat", "text.txt"]
