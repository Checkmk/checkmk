#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import stat
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import chain, groupby
from pathlib import Path

import pytest

from omdlib.restore import _clear_site_home


@dataclass(frozen=True)
class File:
    name: str
    content: bytes


@dataclass(frozen=True)
class Symlink:
    name: str
    path: Path


@dataclass(frozen=True)
class FIFO:
    name: str


# We ignore the other types such as devices and sockets for now.
type FileType = File | Symlink | FIFO
type Files = frozenset[FileType]
type Dirs = frozenset[Directory]


@dataclass(frozen=True)
class Directory:
    name: str
    directories: Dirs = field(default_factory=frozenset)
    files: Files = field(default_factory=frozenset)


# Ignore permissions. Additionally, ignore that path segments such as name should be arbitrary
# bytes, where only `/` and `\0` disallowed.
@dataclass(frozen=True)
class RootDir:
    path: Path
    directories: Dirs = field(default_factory=frozenset)
    files: Files = field(default_factory=frozenset)


def _files_to_disk(folder: Path, files: Iterable[FileType]) -> None:
    for file in files:
        path = folder.joinpath(file.name)
        match file:
            case File(_name, content):
                path.write_bytes(content)
            case Symlink(_name, target):
                path.symlink_to(target)
            case FIFO():
                os.mkfifo(path)


def _recursive_to_disk(
    parent_folder: Path, directories: Iterable[Directory], files: Iterable[FileType]
) -> None:
    for directory in directories:
        dir_path = parent_folder.joinpath(directory.name)
        dir_path.mkdir()
        _recursive_to_disk(dir_path, directory.directories, directory.files)
    _files_to_disk(parent_folder, files)


def _to_disk(root: RootDir) -> None:
    _recursive_to_disk(root.path, directories=root.directories, files=root.files)


def _recursive_from_disk(folder: Path) -> tuple[Dirs, Files]:
    directories: set[Directory] = set()
    files: set[FileType] = set()

    with os.scandir(folder) as scaniter:
        for entry in scaniter:
            path = Path(entry.path)
            if entry.is_symlink():
                files.add(Symlink(name=entry.name, path=path.readlink()))

            elif entry.is_dir(follow_symlinks=False):
                sub_dirs, sub_files = _recursive_from_disk(path)
                directories.add(Directory(name=entry.name, directories=sub_dirs, files=sub_files))
            elif entry.is_file(follow_symlinks=False):
                files.add(File(name=entry.name, content=path.read_bytes()))
            elif stat.S_ISFIFO(entry.stat(follow_symlinks=False).st_mode):
                files.add(FIFO(name=entry.name))
            else:
                # Sockets, block devices, char devices
                raise NotImplementedError()
    return frozenset(directories), frozenset(files)


def _from_disk(path: Path) -> RootDir:
    sub_dirs, sub_files = _recursive_from_disk(path)
    return RootDir(path=path, directories=sub_dirs, files=sub_files)


def _merge_file_lists(files1: Files, files2: Files) -> Files:
    merged = files1 | files2
    names = [file.name for file in merged]
    assert len(names) == len(set(names))
    return merged


def _merge_directories(dirs_one: Iterable[Directory], dirs_two: Iterable[Directory]) -> Dirs:
    result = set()

    def by_name(dir_: Directory) -> str:
        return dir_.name

    for name, dirs in groupby(sorted(chain(dirs_one, dirs_two), key=by_name), key=by_name):
        match list(dirs):
            case [dir_]:
                result.add(dir_)
            case [dir_one, dir_two]:
                merged_files = _merge_file_lists(dir_one.files, dir_two.files)
                merged_dirs = _merge_directories(dir_one.directories, dir_two.directories)
                file_names = {file.name for file in merged_files}
                assert not any(dir_.name in file_names for dir_ in merged_dirs)
                result.add(Directory(name=name, files=merged_files, directories=merged_dirs))
            case _:
                raise ValueError("duplicate directory names")
    return frozenset(result)


@pytest.mark.parametrize(
    "directories, files, untouched",
    [
        (
            frozenset(
                {
                    Directory(
                        name="etc",
                        files=frozenset(
                            {File("environment", content=b"# Custom environment variables\n")}
                        ),
                    ),
                    Directory(
                        name="var",
                        files=frozenset({File("rand.txt", content=b"abc")}),
                    ),
                }
            ),
            frozenset(),
            frozenset(
                {
                    Directory(
                        name="var",
                        directories=frozenset(
                            {
                                Directory(
                                    name="clickhouse-server",
                                    files=frozenset({File("data", content=b"abc")}),
                                )
                            }
                        ),
                    ),
                    Directory(name=".restore_working_dir"),
                }
            ),
        ),
        (
            frozenset(
                {
                    Directory(
                        name="etc",
                        directories=frozenset(
                            {
                                Directory(
                                    name="jaeger",
                                    files=frozenset({File("data", content=b"abc")}),
                                )
                            }
                        ),
                    ),
                }
            ),
            frozenset(),
            frozenset(
                {
                    Directory(
                        name="var",
                        directories=frozenset(
                            {
                                Directory(
                                    name="clickhouse-server",
                                    files=frozenset({File("data", content=b"abc")}),
                                )
                            }
                        ),
                    ),
                    Directory(name=".restore_working_dir"),
                }
            ),
        ),
        (
            frozenset(),
            frozenset({FIFO(name="a pipe")}),
            frozenset({Directory(name=".restore_working_dir")}),
        ),
        (
            frozenset(),
            frozenset({Symlink(name="a link", path=Path("../up"))}),
            frozenset({Directory(name=".restore_working_dir")}),
        ),
    ],
)
def test_clear_site_home(directories: Dirs, files: Files, untouched: Dirs, tmp_path: Path) -> None:
    # Assemble
    _to_disk(
        RootDir(path=tmp_path, directories=_merge_directories(directories, untouched), files=files)
    )
    # Act
    _clear_site_home(tmp_path)
    # Assert
    assert _from_disk(tmp_path) == RootDir(path=tmp_path, directories=untouched)
