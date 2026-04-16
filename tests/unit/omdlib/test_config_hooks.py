#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.config_hooks import (
    _build_site_configs,
    _default_APACHE_TCP_PORT,
    _Error,
    _next_free_port,
    _report_error,
    _set_livestatus_tcp_port,
    _write_livestatus_xinetd_conf_file,
)


def _make_site(sites_dir: Path, name: str, conf: str) -> None:
    etc = sites_dir / name / "etc/omd"
    etc.mkdir(parents=True, exist_ok=True)
    (etc / "site.conf").write_text(conf)


def test_next_free_port_many_sites(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "site1", "CONFIG_APACHE_TCP_PORT='5000'\n")  # blocks 5000
    _make_site(sites, "site2", "CONFIG_APACHE_TCP_PORT='5001'\n")  # blocks 5001
    _make_site(sites, "site3", "# CONFIG_APACHE_TCP_PORT='5002'\n")  # comment, which does not block
    (sites / "ghost").mkdir(parents=True)  # no site.conf — warns but does not block
    (sites / "stray_file").write_text("ignored")  # non-directory entry — skipped silently

    site_configs = _build_site_configs("site3", tmp_path)
    _report_error("APACHE_TCP_PORT", site_configs.sites_with_unreadable_configs)
    assert _next_free_port("APACHE_TCP_PORT", "site3", 5000, site_configs.configs) == 5002
    assert "ghost" in capsys.readouterr().err


def test_next_free_port_different_key(tmp_path: Path) -> None:
    # Different key using port — cross-key conflicts are still detected.
    sites = tmp_path / "sites"
    _make_site(sites, "site1", "CONFIG_LIVESTATUS_TCP_PORT='5000'\n")
    _make_site(sites, "site2", "CONFIG_LIVESTATUS_TCP_PORT='5001'\n")

    site_configs = _build_site_configs("site1", tmp_path)
    assert _next_free_port("APACHE_TCP_PORT", "site1", 5000, site_configs.configs) == 5002


def test_next_free_port_no_conflict(tmp_path: Path) -> None:
    # Same key on current site: not a conflict (port already belongs to this key).
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "CONFIG_APACHE_TCP_PORT='5000'\n")

    site_configs = _build_site_configs("mysite", tmp_path)
    assert _next_free_port("APACHE_TCP_PORT", "mysite", 5000, site_configs.configs) == 5000


def test_next_free_port_missing_config_current_site(tmp_path: Path) -> None:
    # Missing site.conf for current site, happens during site creation.
    sites = tmp_path / "sites"
    (sites / "newsite").mkdir(parents=True)

    site_configs = _build_site_configs("newsite", tmp_path)
    assert _next_free_port("APACHE_TCP_PORT", "newsite", 5000, site_configs.configs) == 5000


def test_set_livestatus_tcp_port_no_conflict(tmp_path: Path) -> None:
    # Port is free. xinetd.conf is rewritten with the same port, value returned.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "CONFIG_LIVESTATUS_TCP_PORT='6557'\n")
    config = {"LIVESTATUS_TCP": "on", "LIVESTATUS_TCP_ONLY_FROM": ""}
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    result = _set_livestatus_tcp_port("mysite", config, tmp_path, "6557")
    assert isinstance(result, str)

    assert result == "6557"
    assert "port = 6557" in conf.read_text()


def test_set_livestatus_tcp_port_conflict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Port 6557 taken by another site. Pick 6558 and warn.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "other", "CONFIG_LIVESTATUS_TCP_PORT='6557'\n")
    _make_site(site_dir.parent, "mysite", "")
    config = {"LIVESTATUS_TCP": "on", "LIVESTATUS_TCP_ONLY_FROM": ""}
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    result = _set_livestatus_tcp_port("mysite", config, tmp_path, "6557")
    assert isinstance(result, str)

    assert result == "6558"
    assert "port = 6558" in conf.read_text()
    assert "port = 6557" not in conf.read_text()
    err = capsys.readouterr().err
    assert "6557" in err
    assert "6558" in err


def test_set_livestatus_tcp_port_invalid_value(tmp_path: Path) -> None:
    # Non-integer port value causes _Error.
    _make_site(tmp_path / "sites", "mysite", "")
    config = {"LIVESTATUS_TCP": "on", "LIVESTATUS_TCP_ONLY_FROM": ""}

    result = _set_livestatus_tcp_port("mysite", config, tmp_path, "not-a-port")

    assert isinstance(result, _Error)


def test_write_livestatus_xinetd_conf_file_with_only_from(tmp_path: Path) -> None:
    # The only_from line is always present; the value must match what was passed.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    _write_livestatus_xinetd_conf_file("mysite", "on", "192.168.0.0/24", "6557", tmp_path)
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    text = conf.read_text()
    assert "only_from       = 192.168.0.0/24" in text
    assert text.count("only_from") == 1


def test_write_livestatus_xinetd_conf_file_update_only_from(tmp_path: Path) -> None:
    # An already-set value is replaced.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    _write_livestatus_xinetd_conf_file("mysite", "on", "10.0.0.2 10.0.0.3", "6557", tmp_path)
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    assert "only_from       = 10.0.0.2 10.0.0.3" in conf.read_text()
    assert "10.0.0.1" not in conf.read_text()


def test_write_livestatus_xinetd_conf_file_without_only_from(tmp_path: Path) -> None:
    # When only_from is empty, the line is still written with an empty value.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    _write_livestatus_xinetd_conf_file("mysite", "on", "", "6557", tmp_path)
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    assert "only_from       = " in conf.read_text()


def test_write_livestatus_xinetd_conf_file_off_writes_header_only(tmp_path: Path) -> None:
    # When LIVESTATUS_TCP is "off", a header-only file is written (no service block).
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    _write_livestatus_xinetd_conf_file("mysite", "off", "", "6557", tmp_path)
    assert conf.exists()
    assert "service livestatus" not in conf.read_text()


def test_default_APACHE_TCP_PORT_cross_key_conflict(tmp_path: Path) -> None:
    # Port 5000 is used by a different config key on another site.
    sites = tmp_path / "sites"
    _make_site(sites, "other", "CONFIG_LIVESTATUS_TCP_PORT='5000'\n")
    _make_site(sites, "mysite", "")

    site_configs = _build_site_configs("mysite", tmp_path)
    assert _default_APACHE_TCP_PORT("mysite", site_configs) == "5001"


def test_default_APACHE_TCP_PORT_warns_on_unreadable_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A site directory without a readable site.conf triggers a stderr warning.
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "")
    (sites / "ghost").mkdir(parents=True)  # no site.conf

    site_configs = _build_site_configs("mysite", tmp_path)
    _default_APACHE_TCP_PORT("mysite", site_configs)

    assert "ghost" in capsys.readouterr().err
