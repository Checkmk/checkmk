#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import stat
from hashlib import sha256
from pathlib import Path

import pytest
from mock import MagicMock
from pytest_mock import MockerFixture

from omdlib.contexts import SiteContext
from omdlib.system_apache import (
    apache_hook_version,
    create_apache_hook,
    create_old_apache_hook,
    delete_apache_hook,
    has_old_apache_hook_in_site,
    is_apache_hook_up_to_date,
    register_with_system_apache,
    unregister_from_system_apache,
)
from omdlib.version_info import VersionInfo


@pytest.fixture(name="reload_apache", autouse=True)
def fixture_reload_apache(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("subprocess.call", return_value=0)


@pytest.fixture(autouse=True)
def fake_config(site_context: SiteContext) -> None:
    site_context._config_loaded = True
    site_context._config = {"APACHE_TCP_PORT": "5000", "APACHE_TCP_ADDR": "127.0.0.1"}


@pytest.fixture(autouse=True)
def fake_version_info(version_info: VersionInfo) -> None:
    version_info.APACHE_CTL = "/usr/sbin/apachectl"


@pytest.fixture(name="apache_config")
def fixture_apache_config(tmp_path: Path, site_context: SiteContext) -> Path:
    return tmp_path.joinpath("omd", "apache", f"{site_context.name}.conf")


def test_register_with_system_apache(
    apache_config: Path,
    version_info: VersionInfo,
    site_context: SiteContext,
    reload_apache: MagicMock,
) -> None:
    apache_config.parent.mkdir(parents=True)

    register_with_system_apache(version_info, site_context, apache_reload=True)

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


def test_unregister_from_system_apache(
    apache_config: Path,
    version_info: VersionInfo,
    site_context: SiteContext,
    reload_apache: MagicMock,
) -> None:
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(version_info, site_context, apache_reload=True)
    assert apache_config.exists()
    reload_apache.reset_mock()

    unregister_from_system_apache(version_info, site_context, apache_reload=True)
    assert not apache_config.exists()
    reload_apache.assert_called_once_with(["/usr/sbin/apachectl", "graceful"])


def test_delete_apache_hook(
    apache_config: Path,
    version_info: VersionInfo,
    site_context: SiteContext,
) -> None:
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(version_info, site_context, apache_reload=True)
    assert apache_config.exists()

    delete_apache_hook(site_context.name)
    assert not apache_config.exists()


def test_delete_apache_hook_not_existing(
    apache_config: Path,
    version_info: VersionInfo,
    site_context: SiteContext,
) -> None:
    delete_apache_hook(site_context.name)
    assert not apache_config.exists()


def test_is_apache_hook_up_to_date(
    apache_config: Path,
    site_context: SiteContext,
) -> None:
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(site_context, apache_hook_version())
    assert apache_config.exists()

    assert has_old_apache_hook_in_site(site_context) is False
    assert is_apache_hook_up_to_date(site_context) is True


def test_is_apache_hook_up_to_date_not_readable(
    apache_config: Path,
    site_context: SiteContext,
) -> None:
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(site_context, apache_hook_version())
    assert apache_config.exists()
    apache_config.chmod(0o200)

    with pytest.raises(PermissionError):
        is_apache_hook_up_to_date(site_context)

    with pytest.raises(PermissionError):
        has_old_apache_hook_in_site(site_context)


def test_is_apache_hook_up_to_date_outdated(
    apache_config: Path,
    site_context: SiteContext,
) -> None:
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(site_context, 0)
    assert apache_config.exists()

    assert has_old_apache_hook_in_site(site_context) is False
    assert is_apache_hook_up_to_date(site_context) is False


def test_has_old_apache_hook_in_site(
    apache_config: Path,
    site_context: SiteContext,
) -> None:
    apache_config.parent.mkdir(parents=True)
    with apache_config.open("w") as f:
        f.write(f"Include /omd/sites/{site_context.name}/etc/apache/mode.conf")

    assert is_apache_hook_up_to_date(site_context) is False
    assert has_old_apache_hook_in_site(site_context) is True


def test_has_apache_hook_in_site(
    apache_config: Path,
    site_context: SiteContext,
) -> None:
    apache_config.parent.mkdir(parents=True)
    with apache_config.open("w") as f:
        f.write(f"Include /omd/sites/{site_context.name}/etc/apache/mode.conf")
    assert apache_config.exists()

    assert is_apache_hook_up_to_date(site_context) is False


def test_create_apache_hook_world_readable(
    apache_config: Path,
    site_context: SiteContext,
) -> None:
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(site_context, 0)
    assert bool(apache_config.stat().st_mode & stat.S_IROTH)


def test_create_old_apache_hook(
    site_context: SiteContext,
) -> None:
    apache_own_path = Path(site_context.dir).joinpath("etc/apache/apache-own.conf")
    apache_own_path.parent.mkdir(parents=True)
    create_old_apache_hook(site_context)
    content = apache_own_path.read_text()
    assert content.startswith("# This file is read in by the global Apache")
