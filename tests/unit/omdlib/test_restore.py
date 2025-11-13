#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import stat
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from omdlib.restore import _remove_site_home


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


@dataclass(frozen=True)
class Directory:
    name: str
    directories: Sequence["Directory"] = field(default_factory=list)
    files: Sequence[FileType] = field(default_factory=list)


# Ignore permissions. Additionally, ignore that path segments such as name should be arbitrary
# bytes, where only `/` and `\0` disallowed.
@dataclass(frozen=True)
class RootDir:
    path: Path
    directories: Sequence[Directory] = field(default_factory=list)
    files: Sequence[FileType] = field(default_factory=list)


def _files_to_disk(folder: Path, files: Sequence[FileType]) -> None:
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
    parent_folder: Path, directories: Sequence[Directory], files: Sequence[FileType]
) -> None:
    for directory in directories:
        dir_path = parent_folder.joinpath(directory.name)
        dir_path.mkdir()
        _recursive_to_disk(dir_path, directory.directories, directory.files)
    _files_to_disk(parent_folder, files)


def _to_disk(root: RootDir) -> None:
    _recursive_to_disk(root.path, directories=root.directories, files=root.files)


def _recursive_from_disk(folder: Path) -> tuple[Sequence[Directory], Sequence[FileType]]:
    directories: list[Directory] = []
    files: list[FileType] = []

    with os.scandir(folder) as scaniter:
        for entry in scaniter:
            path = Path(entry.path)
            if entry.is_symlink():
                files.append(Symlink(name=entry.name, path=path.readlink()))

            elif entry.is_dir(follow_symlinks=False):
                sub_dirs, sub_files = _recursive_from_disk(path)
                directories.append(
                    Directory(name=entry.name, directories=sub_dirs, files=sub_files)
                )
            elif entry.is_file(follow_symlinks=False):
                files.append(File(name=entry.name, content=path.read_bytes()))
            elif stat.S_ISFIFO(entry.stat(follow_symlinks=False).st_mode):
                files.append(FIFO(name=entry.name))
            else:
                # Sockets, block devices, char devices
                raise NotImplementedError()
    return directories, files


def _from_disk(path: Path) -> RootDir:
    sub_dirs, sub_files = _recursive_from_disk(path)
    return RootDir(path=path, directories=sub_dirs, files=sub_files)


@pytest.mark.parametrize(
    "directories, files",
    [
        (
            [
                Directory(
                    name="jaeger",
                    files=[File("test", content=b"abc")],
                ),
                Directory(name=".restore_working_dir"),
                Directory(
                    name="var",
                    files=[File("rand.txt", content=b"abc")],
                    directories=[
                        Directory(name="clickhouse-server", files=[File("data", content=b"abc")])
                    ],
                ),
            ],
            (),
        ),
        (
            [Directory(name=".restore_working_dir")],
            [FIFO(name="a pipe")],
        ),
        (
            [Directory(name=".restore_working_dir")],
            [Symlink(name="a link", path=Path("../up"))],
        ),
    ],
)
def test_remove_site_home(
    directories: Sequence[Directory], files: Sequence[FileType], tmp_path: Path
) -> None:
    _to_disk(RootDir(path=tmp_path, directories=directories, files=files))
    _remove_site_home(tmp_path)
    assert _from_disk(tmp_path) == RootDir(
        path=tmp_path,
        directories=[Directory(name=".restore_working_dir")],
    )
