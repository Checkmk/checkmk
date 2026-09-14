#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import stat
from hashlib import sha256
from pathlib import Path

from pytest_mock import MockerFixture

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
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    reload_apache = mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    register_with_system_apache(
        version_info, apache_config, "unit", "127.0.0.1", "5000", "auto", True, False
    )

    content = apache_config.read_bytes()
    assert (
        sha256(content).hexdigest()
        == "6f2e8d8835e74466698fff7d40931129894602e1de0e0264aeea0adac27932cb"
    ), (
        "The content of [site].conf was changed. Have you updated the apache_hook_version()? The "
        "number needs to be increased with every change to inform the user about an additional step "
        "he has to make. After you did it, you may update the hash here."
    )
    reload_apache.assert_called_once_with(["/usr/sbin/apachectl", "graceful"])


def test_apache_hook_publishes_the_oauth_and_mcp_routes(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000", apache_hook_version(), "auto")

    content = apache_config.read_text()
    # RFC 9728 protected-resource-metadata, public, routed to the site apache.
    assert "/.well-known/oauth-protected-resource/unit/check_mk/mcp" in content
    assert "Require all granted" in content
    # RFC 8414 authorization-server metadata plus the issuer-nested endpoints.
    assert "<Location /.well-known/oauth-authorization-server/oauth-unit>" in content
    assert "<Location /oauth-unit/authorize>" in content
    assert "<Location /oauth-unit/token>" in content
    assert "<Location /oauth-unit/register>" in content


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

    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000", apache_hook_version(), "auto")

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

    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000", apache_hook_version(), "auto")

    content = apache_config.read_text()
    in_locations = sum(s.count("RequestHeader set") for s in _location_sections(content))
    assert in_locations == content.count("RequestHeader set")


def test_create_apache_hook_manual_forwarded_headers_skips_the_directives(
    tmp_path: Path,
) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)

    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000", apache_hook_version(), "manual")

    content = apache_config.read_text()
    assert "<IfModule headers_module>" not in content
    assert "APACHE_FORWARDED_HEADERS is set to 'manual'" in content


def test_unregister_from_system_apache(tmp_path: Path, mocker: MockerFixture) -> None:
    version_info = VersionInfo(tmp_path)
    version_info.APACHE_CTL = "/usr/sbin/apachectl"
    reload_apache = mocker.patch("subprocess.call", return_value=0)
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    register_with_system_apache(
        version_info, apache_config, "unit", "127.0.0.1", "5000", "auto", True, False
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
        version_info, apache_config, "unit", "127.0.0.1", "5000", "auto", True, verbose=False
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


def test_is_apache_hook_up_to_date(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000", apache_hook_version(), "auto")
    assert apache_config.exists()

    assert is_apache_hook_up_to_date(apache_config) is True


def test_is_apache_hook_up_to_date_outdated(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000", 0, "auto")
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
    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000", 0, "auto")
    assert apache_config.stat().st_mode & stat.S_IROTH


def test_create_apache_hook_denies_the_introspection_endpoint(tmp_path: Path) -> None:
    apache_config = tmp_path / "omd/apache/unit.conf"
    apache_config.parent.mkdir(parents=True)
    create_apache_hook(apache_config, "unit", "127.0.0.1", "5000", apache_hook_version(), "auto")

    content = apache_config.read_text()
    assert "<Location /unit/check_mk/oauth_introspect.py>\n    Require all denied" in content
