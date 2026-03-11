#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

from omdlib.tmpfs import _restore_tmpfs_dump, add_to_fstab, save_tmpfs_dump
from omdlib.utils import delete_directory_contents


def test_add_to_fstab_not_existing(tmp_path: Path) -> None:
    fstab_path = tmp_path / "fstab"
    real_tmp_dir = str(tmp_path / "opt/omd/sites/unit/tmp")
    assert not fstab_path.exists()
    add_to_fstab("unit", real_tmp_dir, None, fstab_path)
    assert not fstab_path.exists()


def test_add_to_fstab(tmp_path: Path) -> None:
    fstab_path = tmp_path / "fstab"
    real_tmp_dir = str(tmp_path / "opt/omd/sites/unit/tmp")
    fstab_path.open("w", encoding="utf-8").write("# system fstab bla\n")
    add_to_fstab("unit", real_tmp_dir, None, fstab_path)
    assert fstab_path.open().read() == (
        "# system fstab bla\n"
        f"tmpfs  {real_tmp_dir} tmpfs noauto,user,mode=751,uid=unit,gid=unit 0 0\n"
    )


def test_add_to_fstab_with_size(tmp_path: Path) -> None:
    fstab_path = tmp_path / "fstab"
    real_tmp_dir = str(tmp_path / "opt/omd/sites/unit/tmp")
    fstab_path.open("w", encoding="utf-8").write("# system fstab bla\n")
    add_to_fstab("unit", real_tmp_dir, tmpfs_size="1G", fstab_path=fstab_path)
    assert fstab_path.open().read() == (
        "# system fstab bla\n"
        f"tmpfs  {real_tmp_dir} tmpfs noauto,user,mode=751,uid=unit,gid=unit,size=1G 0 0\n"
    )


def test_add_to_fstab_no_newline_at_end(tmp_path: Path) -> None:
    fstab_path = tmp_path / "fstab"
    real_tmp_dir = str(tmp_path / "opt/omd/sites/unit/tmp")
    fstab_path.open("w", encoding="utf-8").write("# system fstab bla")
    add_to_fstab("unit", real_tmp_dir, None, fstab_path)
    assert fstab_path.open().read() == (
        "# system fstab bla\n"
        f"tmpfs  {real_tmp_dir} tmpfs noauto,user,mode=751,uid=unit,gid=unit 0 0\n"
    )


def test_add_to_fstab_empty(tmp_path: Path) -> None:
    fstab_path = tmp_path / "fstab"
    real_tmp_dir = str(tmp_path / "opt/omd/sites/unit/tmp")
    fstab_path.open("w", encoding="utf-8").write("")
    add_to_fstab("unit", real_tmp_dir, None, fstab_path)
    assert fstab_path.open().read() == (
        f"tmpfs  {real_tmp_dir} tmpfs noauto,user,mode=751,uid=unit,gid=unit 0 0\n"
    )


def test_tmpfs_save_then_restore(tmp_path: Path) -> None:
    site_dir = str(tmp_path)
    site_tmp_dir = str(tmp_path / "tmp_dir")
    tmpfs_dump_path = Path(site_dir) / "var/omd/tmpfs-dump.tar"
    # Create something to restore
    restored_tmp_files = [
        Path(site_tmp_dir) / "check_mk/piggyback/backed/pig",
        Path(site_tmp_dir) / "check_mk/piggyback_sources/pig",
    ]
    for file in restored_tmp_files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("restored!")

    unrestored_tmp_file = Path(site_tmp_dir) / "unrestored"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("unrestored!")
    tmp_files = restored_tmp_files + [unrestored_tmp_file]

    # Now perform unmount call and test result
    assert not tmpfs_dump_path.exists()
    save_tmpfs_dump(site_dir, site_tmp_dir)
    delete_directory_contents(site_tmp_dir)
    assert all(not file.exists() for file in tmp_files)

    assert tmpfs_dump_path.exists()
    _restore_tmpfs_dump(site_dir, site_tmp_dir)
    assert all(file.exists() for file in restored_tmp_files)

    # Test that out-of-scope files are not restored
    assert not unrestored_tmp_file.exists()


def test_tmpfs_mount_no_dump(tmp_path: Path) -> None:
    site_dir = tmp_path
    site_tmp_dir = tmp_path / "tmp_dir"
    site_tmp_dir.mkdir(parents=True, exist_ok=True)

    # Ensure that no dump exists and then execute the restore operation
    _restore_tmpfs_dump(str(site_dir), str(site_tmp_dir))
    assert not any(file.exists() for file in site_tmp_dir.iterdir())
