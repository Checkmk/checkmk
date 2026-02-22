#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import tarfile
from pathlib import Path

import pytest

import omdlib
import omdlib.backup
from omdlib.backup import get_exclude_patterns
from omdlib.options import CommandOptions


def test_backup_site_to_tarfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(omdlib, "__version__", "1.3.3i7.cee")
    site_name = "site"
    site_home = tmp_path / site_name
    site_home.mkdir(parents=True, exist_ok=True)
    (site_home / "version").symlink_to("../versions/%s" % omdlib.__version__)
    # Write some file for testing the backup procedure
    with Path(site_home, "test123").open("w", encoding="utf-8") as f:
        f.write("uftauftauftata")

    tar_path = tmp_path / "backup.tar"
    with tarfile.open(tar_path, mode="w:") as tar:
        omdlib.backup._backup_site_to_tarfile(
            site_name, str(site_home), True, tar, options={}, verbose=False
        )

    with tarfile.open(name=tar_path, mode="r|*") as tar:
        backup_site_name, version = omdlib.backup.get_site_and_version_from_backup(tar)
        names = [tarinfo.name for tarinfo in tar]
    assert backup_site_name == site_name
    assert version == "1.3.3i7.cee"
    assert f"{site_name}/test123" in names


def test_backup_site_to_tarfile_broken_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(omdlib, "__version__", "1.3.3i7.cee")
    site_name = "site"
    site_home = tmp_path / site_name

    site_home.mkdir(parents=True, exist_ok=True)
    (site_home / "version").symlink_to("../versions/%s" % omdlib.__version__)
    Path(site_home, "link").symlink_to("agag")

    tar_path = tmp_path / "backup.tar"
    with tarfile.open(tar_path, mode="w:") as tar:
        omdlib.backup._backup_site_to_tarfile(
            site_name, str(site_home), True, tar, options={}, verbose=False
        )

    with tarfile.open(name=tar_path, mode="r|*") as tar:
        _sitename, _version = omdlib.backup.get_site_and_version_from_backup(tar)

        link = tar.getmember(f"{site_name}/link")
        assert link.linkname == "agag"


def test_backup_site_to_tarfile_vanishing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(omdlib, "__version__", "1.3.3i7.cee")
    site_name = "site"
    site_home = tmp_path / site_name
    site_home.mkdir(parents=True, exist_ok=True)
    (site_home / "version").symlink_to("../versions/%s" % omdlib.__version__)
    test_dir = Path(site_home, "xyz")
    test_file = test_dir / "test_file"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file.touch()

    orig_gettarinfo = tarfile.TarFile.gettarinfo

    def gettarinfo(self: tarfile.TarFile, name: str, arcname: str) -> tarfile.TarInfo:
        # Remove the test_file here to simulate a vanished file during this step.
        if arcname == f"{site_name}/xyz/test_file":
            test_file.unlink()
        return orig_gettarinfo(self, name, arcname)

    monkeypatch.setattr(tarfile.TarFile, "gettarinfo", gettarinfo)

    tar_path = tmp_path / "backup.tar"
    with tarfile.open(tar_path, mode="w:") as tar:
        omdlib.backup._backup_site_to_tarfile(
            site_name, str(site_home), True, tar, options={}, verbose=False
        )

    assert not test_file.exists()  # check that the monkeypatch worked

    with tarfile.open(name=tar_path, mode="r|*") as tar:
        _sitename, _version = omdlib.backup.get_site_and_version_from_backup(tar)


def test_get_exclude_patterns_default() -> None:
    options: CommandOptions = {}

    actual_excludes = get_exclude_patterns(options)

    assert "tmp/*" in actual_excludes
    assert "var/check_mk/agents/*" not in actual_excludes
    assert "var/log/*/*" not in actual_excludes
    assert "var/check_mk/rrd/*" not in actual_excludes


def test_get_exclude_patterns_no_past() -> None:
    options: CommandOptions = {"no-past": None}

    actual_excludes = get_exclude_patterns(options)

    assert "tmp/*" in actual_excludes
    assert "var/check_mk/agents/*" in actual_excludes
    assert "var/log/*/*" in actual_excludes
    assert "var/check_mk/rrd/*" in actual_excludes


def test_get_exclude_patterns_single() -> None:
    options: CommandOptions = {"no-rrds": None}

    actual_excludes = get_exclude_patterns(options)

    assert "tmp/*" in actual_excludes
    assert "var/check_mk/rrd/*" in actual_excludes
    assert "var/check_mk/agents/*" not in actual_excludes
    assert "var/log/*/*" not in actual_excludes


def test_get_exlude_patterns_mixed() -> None:
    options: CommandOptions = {"no-agents": None, "no-logs": None}

    actual_excludes = get_exclude_patterns(options)

    assert "tmp/*" in actual_excludes
    assert "var/check_mk/agents/*" in actual_excludes
    assert "var/log/*/*" in actual_excludes
    assert "var/check_mk/rrd/*" not in actual_excludes
