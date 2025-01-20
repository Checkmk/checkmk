#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import dataclasses
import os
from pathlib import Path

import pytest

from omdlib.update import (
    _restore_version_meta_dir,
    _store_version_meta_dir,
    file_type,
    ManagedTypes,
    ManageUpdate,
    restore,
    store,
    walk_in_DFS_order,
    walk_managed,
)


@dataclasses.dataclass(frozen=True)
class File:
    path: Path
    permission: str
    content: bytes


@dataclasses.dataclass(frozen=True)
class Dir:
    path: Path
    permission: str


@dataclasses.dataclass(frozen=True)
class Symlink:
    path: Path
    content: Path


Entry = File | Dir | Symlink


def read_all(path: Path) -> Entry | None:
    match file_type(path):
        case ManagedTypes.file:
            return File(path=path, permission=oct(os.stat(path).st_mode), content=path.read_bytes())
        case ManagedTypes.directory:
            return Dir(path=path, permission=oct(os.stat(path).st_mode))
        case ManagedTypes.symlink:
            return Symlink(path=path, content=path.readlink())
        case ManagedTypes.missing | ManagedTypes.unknown:
            return None
    return None


CONTENTS = [b"a", b"abc", b"a\nb\nc\n"]
PERMISSIONS = [0o777, 0o000, 0o754]


def random_file(path: Path) -> None:
    # FIXME: randomize path
    # FIXME: allow symlinks and directories
    file_content = CONTENTS[0]  # FIXME: randomize
    permission = PERMISSIONS[0]  # FIXME: randomize
    path.write_bytes(file_content)
    path.chmod(permission)


def remove(root: Path, relpath: Path | str) -> None:
    target = root / relpath
    match file_type(target):
        case ManagedTypes.missing:
            pass
        case ManagedTypes.file | ManagedTypes.symlink:
            target.unlink()
        case ManagedTypes.directory:
            target.rmdir()
        case _:
            raise NotImplementedError()


####


def test_store_directory_remove(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup directory
    relpath = Path("directory")
    directory = tmp_path / relpath
    directory.mkdir()
    os.chmod(directory, 0o754)
    stats_directory = read_all(directory)

    store(tmp_path, relpath, backup_dir)
    remove(tmp_path, relpath)
    assert stats_directory != read_all(directory)
    restore(tmp_path, relpath, backup_dir)
    assert stats_directory == read_all(directory)


def test_store_file_remove(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup file
    relpath = Path("file")
    file = tmp_path / relpath
    file.write_bytes(b"abc")
    os.chmod(file, 0o754)
    stats_file = read_all(file)

    store(tmp_path, relpath, backup_dir)
    remove(tmp_path, relpath)
    assert stats_file != read_all(file)
    restore(tmp_path, relpath, backup_dir)
    assert stats_file == read_all(file)


def test_store_symlink_remove(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup file
    relpath = Path("symlink")
    symlink = tmp_path / relpath
    symlink.symlink_to("../abc")
    # Changing file bits is not supported on linux, so no os.chmod here
    stats_symlink = read_all(symlink)
    assert stats_symlink

    store(tmp_path, relpath, backup_dir)
    remove(tmp_path, relpath)
    assert stats_symlink != read_all(symlink)
    restore(tmp_path, relpath, backup_dir)
    assert stats_symlink == read_all(symlink)


def test_store_directory_modify(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup directory
    relpath = Path("directory")
    directory = tmp_path / relpath
    directory.mkdir()
    os.chmod(directory, 0o754)
    stats_directory = read_all(directory)

    store(tmp_path, relpath, backup_dir)
    os.chmod(directory, 0o755)
    assert stats_directory != read_all(directory)
    restore(tmp_path, relpath, backup_dir)
    assert stats_directory == read_all(directory)


def test_store_file_modify(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup file
    relpath = Path("file")
    file = tmp_path / relpath
    file.write_bytes(b"abc")
    os.chmod(file, 0o754)
    stats_file = read_all(file)

    store(tmp_path, relpath, backup_dir)
    os.chmod(file, 0o755)
    file.write_bytes(b"def")
    assert stats_file != read_all(file)
    restore(tmp_path, relpath, backup_dir)
    assert stats_file == read_all(file)


def test_store_symlink_modify(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup file
    relpath = Path("symlink")
    symlink = tmp_path / relpath
    symlink.symlink_to("../abc")
    # Changing file bits is not supported on linux, so no os.chmod here
    stats_symlink = read_all(symlink)
    assert stats_symlink

    store(tmp_path, relpath, backup_dir)
    symlink.unlink()
    symlink.symlink_to("../def")
    assert stats_symlink != read_all(symlink)
    restore(tmp_path, relpath, backup_dir)
    assert stats_symlink == read_all(symlink)


def test_store_directory_add(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup directory
    relpath = Path("directory")
    directory = tmp_path / relpath
    stats_directory = read_all(directory)

    store(tmp_path, relpath, backup_dir)
    directory.mkdir()
    assert stats_directory != read_all(directory)
    restore(tmp_path, relpath, backup_dir)
    assert stats_directory == read_all(directory)


def test_store_file_add(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup file
    relpath = Path("file")
    file = tmp_path / relpath
    stats_file = read_all(file)

    store(tmp_path, relpath, backup_dir)
    file.write_bytes(b"def")
    os.chmod(file, 0o755)
    assert stats_file != read_all(file)
    restore(tmp_path, relpath, backup_dir)
    assert stats_file == read_all(file)


def test_store_symlink_add(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # setup file
    relpath = Path("symlink")
    symlink = tmp_path / relpath
    stats_symlink = read_all(symlink)

    store(tmp_path, relpath, backup_dir)
    symlink.symlink_to("../abc")
    assert stats_symlink != read_all(symlink)
    restore(tmp_path, relpath, backup_dir)
    assert stats_symlink == read_all(symlink)


####


def setup_skel(path: Path) -> None:
    a = path / "a"
    a.mkdir(parents=True)
    bb = path / "aa" / "bb"
    bb.mkdir(parents=True)
    a_1 = a / "1.file"
    random_file(a_1)
    bb_1 = bb / "1.file"
    random_file(bb_1)
    ccc = path / "aaa" / "bbb" / "ccc"
    ccc.mkdir(parents=True)
    ccc_1 = ccc / "1.file"
    random_file(ccc_1)


def setup_user(path: Path) -> None:
    a = path / "a"
    a.mkdir(parents=True, exist_ok=True)
    bb = path / "aa" / "bb"
    bb.mkdir(parents=True, exist_ok=True)
    a_1 = a / "user_1.file"
    random_file(a_1)
    bb_1 = bb / "user_1.file"
    random_file(bb_1)


class TBaseException(BaseException):
    pass


def _list_non_backup_files(site_dir: Path) -> list[Entry]:
    found = [read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)]
    assert all(entry is not None for entry in found)
    return sorted(found, key=lambda entry: str(entry.path))  # type: ignore[arg-type]


def test_backup_remove(tmp_path: Path) -> None:
    new_skel = tmp_path / "new_skel"
    old_skel = tmp_path / "old_skel"
    site_dir = tmp_path / "site_dir"

    new_skel.mkdir()
    setup_skel(old_skel)
    setup_skel(site_dir)
    setup_user(site_dir)

    save = _list_non_backup_files(site_dir)

    with contextlib.suppress(TBaseException):
        with ManageUpdate("heute", "tmp_directory", site_dir, old_skel, new_skel):
            assert save == _list_non_backup_files(site_dir)
            for relpath in reversed(list(walk_managed(old_skel))):
                with contextlib.suppress(OSError):
                    remove(site_dir, relpath)
            assert save != _list_non_backup_files(site_dir)
            raise TBaseException()
    assert save == _list_non_backup_files(site_dir)


def test_backup_add(tmp_path: Path) -> None:
    new_skel = tmp_path / "new_skel"
    old_skel = tmp_path / "old_skel"
    site_dir = tmp_path / "site_dir"

    old_skel.mkdir()
    setup_skel(new_skel)
    setup_user(site_dir)
    save = [read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)]

    with contextlib.suppress(TBaseException):
        with ManageUpdate("heute", "tmp_directory", site_dir, old_skel, new_skel):
            assert save == [
                read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)
            ]
            for relpath in walk_managed(new_skel):
                restore(site_dir, relpath, new_skel)
            assert save != [
                read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)
            ]
            raise TBaseException()
    assert save == [
        read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)
    ]


@pytest.mark.xfail(strict=True)
def test_backup_modify(tmp_path: Path) -> None:
    new_skel = tmp_path / "new_skel"
    old_skel = tmp_path / "old_skel"
    site_dir = tmp_path / "site_dir"

    old_skel.mkdir()
    setup_skel(new_skel)
    for path in walk_in_DFS_order(new_skel):
        path.chmod(0o754)
    setup_skel(old_skel)
    setup_skel(site_dir)
    setup_user(site_dir)
    site_dir.chmod(0o751)
    save = [read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)]

    with contextlib.suppress(TBaseException):
        with ManageUpdate("heute", "tmp_directory", site_dir, old_skel, new_skel):
            assert save == [
                read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)
            ]
            for relpath in walk_managed(new_skel):
                (site_dir / relpath).chmod(0o754)
            assert save != [
                read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)
            ]
            raise TBaseException()
    assert save == [
        read_all(p) for p in walk_in_DFS_order(site_dir) if ".update_backup" not in str(p)
    ]


def test_backup_prepare_next_run(tmp_path: Path) -> None:
    new_skel = tmp_path / "new_skel"
    new_skel.mkdir()
    old_skel = tmp_path / "old_skel"
    old_skel.mkdir()
    site_dir = tmp_path / "site_dir"
    site_dir.mkdir()

    with contextlib.suppress(TBaseException):
        with ManageUpdate("heute", "tmp_directory", site_dir, old_skel, new_skel) as mu:
            backup_dir = mu.backup_dir
            assert backup_dir.exists()
    assert not backup_dir.exists()


def test_restore_version_meta_dir(tmp_path: Path) -> None:
    site_dir = tmp_path / "site_dir"
    site_dir.mkdir()
    backup_dir = tmp_path / ".update_backup"
    backup_dir.mkdir()
    version_metadir = site_dir / ".version_meta"
    version_metadir.mkdir()
    version_file = version_metadir / "version"
    random_file(version_file)
    save = [read_all(p) for p in walk_in_DFS_order(version_metadir)]

    _store_version_meta_dir(site_dir, backup_dir)
    assert save == [read_all(p) for p in walk_in_DFS_order(version_metadir)]
    version_file.unlink()
    assert save != [read_all(p) for p in walk_in_DFS_order(version_metadir)]
    _restore_version_meta_dir(site_dir, backup_dir)
    assert save == [read_all(p) for p in walk_in_DFS_order(version_metadir)]
