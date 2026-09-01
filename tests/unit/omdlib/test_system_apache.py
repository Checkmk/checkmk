#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import stat
from pathlib import Path

from pytest_mock import MockerFixture

from omdlib.system_apache import (
    create_apache_hook,
    delete_apache_hook,
    register_with_system_apache,
    unregister_from_system_apache,
    write_apache_listen_conf,
)
from omdlib.version_info import VersionInfo


def test_register_with_system_apache(tmp_path: Path, mocker: MockerFixture) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    reload_apache = mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    register_with_system_apache(
        version_info, apache_config, "unit", "127.0.0.1", "5000", True, False
    )

    assert apache_config.exists()
    reload_apache.assert_called_once_with(["/usr/sbin/apachectl", "graceful"])


def test_apache_hook_publishes_the_public_mcp_prm_route(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000")

    content = apache_config.read_text()
    assert "/.well-known/oauth-protected-resource/unit/check_mk/mcp" in content
    assert "Require all granted" in content


def test_unregister_from_system_apache(tmp_path: Path, mocker: MockerFixture) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    reload_apache = mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(
        version_info, apache_config, "unit", "127.0.0.1", "5000", True, False
    )
    assert apache_config.exists()
    reload_apache.reset_mock()

    unregister_from_system_apache(version_info, apache_config, apache_reload=True, verbose=False)
    assert not apache_config.exists()
    reload_apache.assert_called_once_with(["/usr/sbin/apachectl", "graceful"])


def test_delete_apache_hook(tmp_path: Path) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(
        version_info, apache_config, "unit", "127.0.0.1", "5000", True, verbose=False
    )
    assert apache_config.exists()

    delete_apache_hook(apache_config)
    assert not apache_config.exists()


def test_delete_apache_hook_not_existing(tmp_path: Path) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    apache_config = tmp_path / "omd/apache/unit.conf"
    delete_apache_hook(apache_config)
    assert not apache_config.exists()


def test_create_apache_hook_world_readable(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000")
    assert apache_config.stat().st_mode & stat.S_IROTH


def test_create_apache_hook_well_known_oauth_authorization_server(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000")

    content = apache_config.read_text()
    assert "<Location /.well-known/oauth-authorization-server/oauth-unit>" in content
    assert "ProxyPass http://127.0.0.1:5000/unit/check_mk/oauth_authorization_server.py" in content


def test_create_apache_hook_oauth_authorization_server_endpoints(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000")

    content = apache_config.read_text()
    assert "<Location /oauth-unit/authorize>" in content
    assert "ProxyPass http://127.0.0.1:5000/unit/check_mk/oauth_authorize.py" in content
    assert "<Location /oauth-unit/token>" in content
    assert "ProxyPass http://127.0.0.1:5000/unit/check_mk/oauth_token.py" in content
    assert "<Location /oauth-unit/register>" in content
    assert "ProxyPass http://127.0.0.1:5000/unit/check_mk/oauth_client_registration.py" in content


def test_create_apache_hook_denies_the_introspection_endpoint(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000")

    content = apache_config.read_text()
    assert "<Location /unit/check_mk/oauth_introspect.py>\n    Require all denied" in content


def test_write_apache_listen_conf_ipv4(tmp_path: Path) -> None:
    (tmp_path / "etc/apache").mkdir(parents=True)
    write_apache_listen_conf(
        "mysite", tmp_path, {"APACHE_TCP_ADDR": "127.0.0.1", "APACHE_TCP_PORT": "5000"}
    )
    content = (tmp_path / "etc/apache/listen-port.conf").read_text()
    assert "ServerName 127.0.0.1:5000" in content
    assert "Listen 127.0.0.1:5000" in content


def test_write_apache_listen_conf_ipv6(tmp_path: Path) -> None:
    (tmp_path / "etc/apache").mkdir(parents=True)
    write_apache_listen_conf(
        "mysite", tmp_path, {"APACHE_TCP_ADDR": "[::1]", "APACHE_TCP_PORT": "5000"}
    )
    content = (tmp_path / "etc/apache/listen-port.conf").read_text()
    assert "Listen [::1]:5000" in content
    assert "ServerName" not in content
