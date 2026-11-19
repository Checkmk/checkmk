#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import stat
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from omdlib.sites import is_disabled
from omdlib.system_apache import (
    apache_hook_status,
    ApacheHookState,
    ApacheHookStatus,
    ApacheSettings,
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

    register_with_system_apache(version_info, apache_config, "unit", _settings(), True, False)

    assert apache_config.exists()
    reload_apache.assert_called_once_with(["/usr/sbin/apachectl", "graceful"])


def test_create_apache_hook_proxies_to_the_site_apache(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    create_apache_hook(apache_config, "unit", _settings(addr="127.0.0.2", port="5001"))

    content = apache_config.read_text()
    assert "<Proxy http://127.0.0.2:5001/unit>" in content
    assert "ProxyPass http://127.0.0.2:5001/unit retry=0" in content


def test_apache_hook_publishes_the_public_mcp_prm_route(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    create_apache_hook(apache_config, "unit", _settings())

    content = apache_config.read_text()
    assert "/.well-known/oauth-protected-resource/unit/check_mk/mcp" in content
    assert "Require all granted" in content


def _location_sections(content: str) -> list[str]:
    sections = []
    current: list[str] | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("<Location "):
            current = []
        elif stripped == "</Location>" and current is not None:
            sections.append("\n".join(current))
            current = None
        elif current is not None:
            current.append(stripped)
    return sections


def test_create_apache_hook_forwards_scheme_headers_in_every_proxied_location(
    tmp_path: Path,
) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    create_apache_hook(apache_config, "unit", _settings())

    proxied = [s for s in _location_sections(apache_config.read_text()) if "ProxyPass " in s]
    assert proxied
    for section in proxied:
        assert "RequestHeader set X-Forwarded-Proto expr=%{REQUEST_SCHEME}" in section
        assert "RequestHeader set X-Forwarded-Ssl expr=%{HTTPS}" in section


def test_create_apache_hook_sets_scheme_headers_only_for_the_site(tmp_path: Path) -> None:
    # All sites' hooks are loaded into the same system Apache: a server-wide RequestHeader
    # would also apply to the other sites' requests.
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    create_apache_hook(apache_config, "unit", _settings())

    content = apache_config.read_text()
    in_locations = sum(s.count("RequestHeader set") for s in _location_sections(content))
    assert in_locations == content.count("RequestHeader set")


def test_create_apache_hook_manual_forwarded_headers_skips_the_directives(
    tmp_path: Path,
) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    create_apache_hook(apache_config, "unit", _settings(forwarded_headers="manual"))

    content = apache_config.read_text()
    assert "<IfModule headers_module>" not in content
    assert "APACHE_FORWARDED_HEADERS is set to 'manual'" in content


def _settings(
    addr: str = "127.0.0.1",
    port: str = "5000",
    mode: str = "own",
    forwarded_headers: str = "auto",
) -> ApacheSettings:
    return ApacheSettings(
        mode=mode, tcp_addr=addr, tcp_port=port, forwarded_headers=forwarded_headers
    )


def test_unregister_from_system_apache(tmp_path: Path, mocker: MockerFixture) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    reload_apache = mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(version_info, apache_config, "unit", _settings(), True, False)
    assert apache_config.exists()
    reload_apache.reset_mock()

    unregister_from_system_apache(version_info, apache_config, apache_reload=True, verbose=False)
    assert not apache_config.exists()
    reload_apache.assert_called_once_with(["/usr/sbin/apachectl", "graceful"])


def test_register_with_mode_none_keeps_the_site_enabled(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"

    register_with_system_apache(
        version_info, apache_config, "unit", _settings(mode="none"), True, False
    )

    assert not is_disabled(apache_config)


def test_register_with_mode_none_replaces_the_proxy_configuration(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", _settings())

    register_with_system_apache(
        version_info, apache_config, "unit", _settings(mode="none"), True, False
    )

    assert "ProxyPass" not in apache_config.read_text()


def test_delete_apache_hook(tmp_path: Path) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(
        version_info, apache_config, "unit", _settings(), True, verbose=False
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
    create_apache_hook(apache_config, "unit", _settings())
    assert apache_config.stat().st_mode & stat.S_IROTH


def test_create_apache_hook_well_known_oauth_authorization_server(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", _settings())

    content = apache_config.read_text()
    assert "<Location /.well-known/oauth-authorization-server/oauth-unit>" in content
    assert "ProxyPass http://127.0.0.1:5000/unit/check_mk/oauth_authorization_server.py" in content


def test_create_apache_hook_oauth_authorization_server_endpoints(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", _settings())

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
    create_apache_hook(apache_config, "unit", _settings())

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


_MANAGED = "# This file is managed by 'omd' and will automatically be overwritten. Better do not edit manually\n"


def test_hook_written_with_the_settings_is_up_to_date(tmp_path: Path) -> None:
    apache_config = tmp_path / "unit.conf"
    create_apache_hook(apache_config, "unit", _settings())

    assert apache_hook_status(apache_config, _settings()) == ApacheHookStatus(
        ApacheHookState.UP_TO_DATE
    )


@pytest.mark.parametrize(
    "changed",
    [
        {"APACHE_TCP_ADDR": "127.0.0.2"},
        {"APACHE_TCP_PORT": "5001"},
        {"APACHE_FORWARDED_HEADERS": "manual"},
        {"APACHE_TCP_ADDR": "127.0.0.2", "APACHE_TCP_PORT": "5001"},
    ],
)
def test_hook_written_with_other_settings_has_changed(
    tmp_path: Path, changed: dict[str, str]
) -> None:
    apache_config = tmp_path / "unit.conf"
    create_apache_hook(apache_config, "unit", _settings())
    site_settings = _settings(
        addr=changed.get("APACHE_TCP_ADDR", "127.0.0.1"),
        port=changed.get("APACHE_TCP_PORT", "5000"),
        forwarded_headers=changed.get("APACHE_FORWARDED_HEADERS", "auto"),
    )

    assert apache_hook_status(apache_config, site_settings) == ApacheHookStatus(
        ApacheHookState.CHANGED, changed
    )


@pytest.mark.parametrize("hook_mode, site_mode", [("own", "none"), ("none", "own")])
def test_changed_mode_hides_the_other_settings(
    tmp_path: Path, hook_mode: str, site_mode: str
) -> None:
    apache_config = tmp_path / "unit.conf"
    create_apache_hook(apache_config, "unit", _settings(mode=hook_mode))

    assert apache_hook_status(
        apache_config, _settings(mode=site_mode, port="5001")
    ) == ApacheHookStatus(ApacheHookState.CHANGED, {"APACHE_MODE": site_mode})


@pytest.mark.parametrize(
    "settings_line",
    [
        pytest.param("", id="no settings line"),
        pytest.param("# settings: APACHE_MODE=own\n", id="no json"),
        pytest.param("# settings: [1, 2]\n", id="no json object"),
    ],
)
def test_managed_hook_without_settings_is_legacy(tmp_path: Path, settings_line: str) -> None:
    apache_config = tmp_path / "unit.conf"
    apache_config.write_text(f"{settings_line}{_MANAGED}")

    assert apache_hook_status(apache_config, _settings()).state is ApacheHookState.LEGACY


def test_missing_hook_is_reported_as_missing(tmp_path: Path) -> None:
    assert apache_hook_status(tmp_path / "unit.conf", _settings()).state is ApacheHookState.MISSING


def test_unreadable_hook_is_reported_as_unreadable(tmp_path: Path) -> None:
    (tmp_path / "unit.conf").mkdir()

    assert (
        apache_hook_status(tmp_path / "unit.conf", _settings()).state is ApacheHookState.UNREADABLE
    )


def test_hook_not_written_by_omd_is_unmanaged(tmp_path: Path) -> None:
    apache_config = tmp_path / "unit.conf"
    apache_config.write_text("Include /omd/sites/unit/etc/apache/mode.conf\n")

    assert apache_hook_status(apache_config, _settings()).state is ApacheHookState.UNMANAGED
