# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for _install_binary unlink-before-copy behavior."""

from __future__ import annotations

import os
from pathlib import Path

from cmk.dev_deploy.deployers.bazel_builder import _install_binary


class TestInstallBinary:
    """Tests for _install_binary with unlink-before-copy."""

    def test_first_install(self, tmp_path: Path) -> None:
        """Binary is installed when destination does not exist."""
        src = tmp_path / "src" / "binary"
        src.parent.mkdir()
        src.write_bytes(b"ELF_CONTENT")
        dest = tmp_path / "site" / "lib" / "binary"

        _install_binary(src, dest, 0o755)

        assert dest.read_bytes() == b"ELF_CONTENT"
        assert os.stat(dest).st_mode & 0o777 == 0o755

    def test_replaces_existing_on_fresh_inode(self, tmp_path: Path) -> None:
        """Existing file is unlinked so the copy creates a new inode."""
        src = tmp_path / "new_binary"
        src.write_bytes(b"NEW_CONTENT")
        dest = tmp_path / "old_binary"
        dest.write_bytes(b"OLD_CONTENT")
        _old_inode = dest.stat().st_ino

        _install_binary(src, dest, 0o755)

        assert dest.read_bytes() == b"NEW_CONTENT"
        # On most filesystems the old inode is freed and a new one is
        # allocated.  We cannot assert st_ino differs (the allocator may
        # reuse it), but we CAN verify the content was replaced and the
        # unlink happened by checking that holding an open fd to the old
        # file does not see the new content.

    def test_open_fd_survives_unlink(self, tmp_path: Path) -> None:
        """A process holding an fd to the old file keeps its data."""
        src = tmp_path / "new_binary"
        src.write_bytes(b"NEW_CONTENT")
        dest = tmp_path / "old_binary"
        dest.write_bytes(b"OLD_CONTENT")

        # Simulate a running process holding an fd to the old file
        with open(dest, "rb") as old_fd:
            _install_binary(src, dest, 0o755)
            # The fd still reads the OLD content (old inode kept alive)
            assert old_fd.read() == b"OLD_CONTENT"

        # But the path now has the NEW content (new inode)
        assert dest.read_bytes() == b"NEW_CONTENT"

    def test_parent_dirs_created(self, tmp_path: Path) -> None:
        """Parent directories of dest are created automatically."""
        src = tmp_path / "binary"
        src.write_bytes(b"CONTENT")
        dest = tmp_path / "a" / "b" / "c" / "binary"

        _install_binary(src, dest, 0o755)

        assert dest.read_bytes() == b"CONTENT"

    def test_mode_is_set(self, tmp_path: Path) -> None:
        """File permissions are applied after copy."""
        src = tmp_path / "binary"
        src.write_bytes(b"CONTENT")
        dest = tmp_path / "out"

        _install_binary(src, dest, 0o644)

        assert os.stat(dest).st_mode & 0o777 == 0o644
