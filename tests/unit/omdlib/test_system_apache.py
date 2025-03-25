#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import stat
from hashlib import sha256
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import omdlib
from omdlib.system_apache import (
    apache_hook_version,
    create_apache_hook,
    delete_apache_hook,
    is_apache_hook_up_to_date,
    register_with_system_apache,
    unregister_from_system_apache,
)
from omdlib.version_info import VersionInfo


def test_register_with_system_apache(tmp_path: Path, mocker: MockerFixture) -> None:
    version_info = VersionInfo(omdlib.__version__)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    reload_apache = mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    register_with_system_apache(
        version_info, apache_config, "unit", str(tmp_path), "127.0.0.1", "5000", True, False
    )

    content = apache_config.read_bytes()
    assert (
        sha256(content).hexdigest()
        == "482227acabe270d7bfd6340153b02438c019aeffbfeb9c720156a152ea058d79"
    ), (
        "The content of [site].conf was changed. Have you updated the apache_hook_version()? The "
        "number needs to be increased with every change to inform the user about an additional step "
        "he has to make. After you did it, you may update the hash here."
    )
    reload_apache.assert_called_once_with(["/usr/sbin/apachectl", "graceful"])


def test_unregister_from_system_apache(tmp_path: Path, mocker: MockerFixture) -> None:
    version_info = VersionInfo(omdlib.__version__)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    reload_apache = mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(
        version_info, apache_config, "unit", str(tmp_path), "127.0.0.1", "5000", True, False
    )
    assert apache_config.exists()
    reload_apache.reset_mock()

    unregister_from_system_apache(version_info, apache_config, apache_reload=True, verbose=False)
    assert not apache_config.exists()
    reload_apache.assert_called_once_with(["/usr/sbin/apachectl", "graceful"])


def test_delete_apache_hook(tmp_path: Path) -> None:
    version_info = VersionInfo(omdlib.__version__)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(
        version_info, apache_config, "unit", str(tmp_path), "127.0.0.1", "5000", True, verbose=False
    )
    assert apache_config.exists()

    delete_apache_hook(apache_config)
    assert not apache_config.exists()


def test_delete_apache_hook_not_existing(tmp_path: Path) -> None:
    version_info = VersionInfo(omdlib.__version__)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    apache_config = tmp_path / "omd/apache/unit.conf"
    delete_apache_hook(apache_config)
    assert not apache_config.exists()


def test_is_apache_hook_up_to_date(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(
        apache_config, "unit", str(tmp_path), "127.0.0.1", "5000", apache_hook_version()
    )
    assert apache_config.exists()

    assert is_apache_hook_up_to_date(apache_config) is True


def test_is_apache_hook_up_to_date_not_readable(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(
        apache_config, "unit", str(tmp_path), "127.0.0.1", "5000", apache_hook_version()
    )
    assert apache_config.exists()
    apache_config.chmod(0o200)

    with pytest.raises(PermissionError):
        is_apache_hook_up_to_date(apache_config)


def test_is_apache_hook_up_to_date_outdated(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", str(tmp_path), "127.0.0.1", "5000", 0)
    assert apache_config.exists()

    assert is_apache_hook_up_to_date(apache_config) is False


def test_has_old_apache_hook_in_site(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    with apache_config.open("w") as f:
        f.write("Include /omd/sites/unit/etc/apache/mode.conf")

    assert is_apache_hook_up_to_date(apache_config) is False


def test_has_apache_hook_in_site(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    with apache_config.open("w") as f:
        f.write("Include /omd/sites/unit/etc/apache/mode.conf")
    assert apache_config.exists()

    assert is_apache_hook_up_to_date(apache_config) is False


def test_create_apache_hook_world_readable(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", str(tmp_path), "127.0.0.1", "5000", 0)
    assert apache_config.stat().st_mode & stat.S_IROTH
