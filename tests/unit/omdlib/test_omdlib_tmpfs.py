#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

import pytest

import omdlib.tmpfs
from omdlib.tmpfs import add_to_fstab, restore_tmpfs_dump, unmount_tmpfs
from omdlib.utils import delete_directory_contents


@pytest.fixture(name="tmp_fstab")
def fixture_tmp_fstab(tmp_path, monkeypatch):
    fstab_path = tmp_path / "fstab"
    monkeypatch.setattr(omdlib.tmpfs, "fstab_path", lambda: fstab_path)
    return fstab_path


@pytest.mark.usefixtures("site_context")
def test_add_to_fstab_not_existing(tmp_fstab, site_context) -> None:
    assert not tmp_fstab.exists()
    add_to_fstab(site_context)
    assert not tmp_fstab.exists()


def test_add_to_fstab(tmp_path, tmp_fstab, site_context) -> None:
    tmp_fstab.open("w", encoding="utf-8").write("# system fstab bla\n")
    add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  %s/opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n"
        % tmp_path
    )


def test_add_to_fstab_with_size(tmp_path, tmp_fstab, site_context) -> None:
    tmp_fstab.open("w", encoding="utf-8").write("# system fstab bla\n")
    add_to_fstab(site_context, tmpfs_size="1G")
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  %s/opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit,size=1G 0 0\n"
        % tmp_path
    )


def test_add_to_fstab_no_newline_at_end(tmp_path, tmp_fstab, site_context) -> None:
    tmp_fstab.open("w", encoding="utf-8").write("# system fstab bla")
    add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  %s/opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n"
        % tmp_path
    )


def test_add_to_fstab_empty(tmp_path, tmp_fstab, site_context) -> None:
    tmp_fstab.open("w", encoding="utf-8").write("")
    add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "tmpfs  %s/opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n"
        % tmp_path
    )


@pytest.fixture(name="not_restored_file")
def fixture_not_restored_file(site_context):
    # Create something that is skipped during restore
    tmp_dir = Path(site_context.tmp_dir)
    tmp_file = tmp_dir.joinpath("not_restored_file")
    tmp_file.parent.mkdir(parents=True, exist_ok=True)
    with tmp_file.open("w") as f:
        f.write("not_restored!")
    assert tmp_file.exists()
    return tmp_file


def _prepare_tmpfs(site_context):
    # Create something to restore
    tmp_dir = Path(site_context.tmp_dir)
    files = []

    tmp_file = tmp_dir.joinpath("check_mk", "piggyback", "backed", "pig")
    tmp_file.parent.mkdir(parents=True, exist_ok=True)
    with tmp_file.open("w") as f:
        f.write("restored!")
    assert tmp_file.exists()
    files.append(tmp_file)

    tmp_file = tmp_dir.joinpath("check_mk", "piggyback_sources", "pig")
    tmp_file.parent.mkdir(parents=True, exist_ok=True)
    with tmp_file.open("w") as f:
        f.write("restored!")
    assert tmp_file.exists()
    files.append(tmp_file)

    return files


def test_tmpfs_restore_no_tmpfs(site_context, monkeypatch, not_restored_file) -> None:
    # Use rm logic in unmount_tmpfs instead of unmount
    monkeypatch.setattr(omdlib.tmpfs, "tmpfs_mounted", lambda x: False)

    tmp_files = _prepare_tmpfs(site_context)

    # Now perform unmount call and test result
    assert not omdlib.tmpfs._tmpfs_dump_path(site_context).exists()
    unmount_tmpfs(site_context)
    for tmp_file in tmp_files:
        assert not tmp_file.exists()

    assert omdlib.tmpfs._tmpfs_dump_path(site_context).exists()
    restore_tmpfs_dump(site_context)
    for tmp_file in tmp_files:
        assert tmp_file.exists()

    # Test that out-of-scope files are not restored
    assert not not_restored_file.exists()


class FakeTMPFS:
    def __init__(self) -> None:
        self.mounted = True

    def unmount(self):
        self.mounted = False

    def mount(self):
        self.mounted = True


@pytest.fixture(name="mock_umount")
def fixture_mock_umount(monkeypatch):
    fake_tmpfs = FakeTMPFS()

    # Use rm logic in unmount_tmpfs instead of unmount
    monkeypatch.setattr(omdlib.tmpfs, "tmpfs_mounted", lambda x: fake_tmpfs.mounted)

    def unmount(site):
        delete_directory_contents(site.tmp_dir)
        fake_tmpfs.unmount()

    # Simulate umount
    monkeypatch.setattr(omdlib.tmpfs, "_unmount", unmount)
    # Disable wait during unmount
    monkeypatch.setattr(time, "sleep", lambda x: None)


@pytest.mark.usefixtures("mock_umount")
def test_tmpfs_restore_with_tmpfs(site_context, monkeypatch, not_restored_file) -> None:
    tmp_files = _prepare_tmpfs(site_context)

    # Now perform unmount call and test result
    assert not omdlib.tmpfs._tmpfs_dump_path(site_context).exists()
    omdlib.tmpfs.unmount_tmpfs(site_context)
    for tmp_file in tmp_files:
        assert not tmp_file.exists()

    assert omdlib.tmpfs._tmpfs_dump_path(site_context).exists()
    restore_tmpfs_dump(site_context)
    for tmp_file in tmp_files:
        assert tmp_file.exists()

    # Test that out-of-scope files are not restored
    assert not not_restored_file.exists()


def test_tmpfs_mount_no_dump(site_context, monkeypatch) -> None:
    tmp_dir = Path(site_context.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Ensure that no dump exists and then execute the restore operation
    assert not omdlib.tmpfs._tmpfs_dump_path(site_context).exists()
    restore_tmpfs_dump(site_context)
    assert list(tmp_dir.iterdir()) == []
