#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.config_hooks import _next_free_port, _set_livestatus_tcp_port


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

    assert _next_free_port("APACHE_TCP_PORT", "site3", 5000, omd_path=tmp_path) == 5002
    assert "ghost" in capsys.readouterr().err


def test_next_free_port_different_key(tmp_path: Path) -> None:
    # Different key using port — cross-key conflicts are still detected.
    sites = tmp_path / "sites"
    _make_site(sites, "site1", "CONFIG_LIVESTATUS_TCP_PORT='5000'\n")
    _make_site(sites, "site2", "CONFIG_LIVESTATUS_TCP_PORT='5001'\n")

    assert _next_free_port("APACHE_TCP_PORT", "site1", 5000, omd_path=tmp_path) == 5002


def test_next_free_port_no_conflict(tmp_path: Path) -> None:
    # Same key on current site: not a conflict (port already belongs to this key).
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "CONFIG_APACHE_TCP_PORT='5000'\n")
    assert _next_free_port("APACHE_TCP_PORT", "mysite", 5000, omd_path=tmp_path) == 5000


def test_next_free_port_missing_config_current_site(tmp_path: Path) -> None:
    # Missing site.conf for current site, happens during site creation.
    sites = tmp_path / "sites"
    (sites / "newsite").mkdir(parents=True)
    assert _next_free_port("APACHE_TCP_PORT", "newsite", 5000, omd_path=tmp_path) == 5000


def _make_xinetd_conf(site_dir: Path, port: int) -> Path:
    conf = site_dir / "etc/mk-livestatus/xinetd.conf"
    conf.parent.mkdir(parents=True, exist_ok=True)
    conf.write_text(f"service livestatus\n{{\n\tport\t\t= {port}\n}}\n")
    return conf


def test_set_livestatus_tcp_port_no_conflict(tmp_path: Path) -> None:
    # Port is free. xinetd.conf is rewritten with the same port, value returned.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "CONFIG_LIVESTATUS_TCP_PORT='6557'\n")
    conf = _make_xinetd_conf(site_dir, 6557)

    result = _set_livestatus_tcp_port("mysite", "6557", omd_path=tmp_path)

    assert result == "6557"
    assert "\tport\t\t= 6557" in conf.read_text()


def test_set_livestatus_tcp_port_conflict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Port 6557 taken by another site. Pick 6558 and warn.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "other", "CONFIG_LIVESTATUS_TCP_PORT='6557'\n")
    _make_site(site_dir.parent, "mysite", "")
    conf = _make_xinetd_conf(site_dir, 6557)

    result = _set_livestatus_tcp_port("mysite", "6557", omd_path=tmp_path)

    assert result == "6558"
    assert "\tport\t\t= 6558" in conf.read_text()
    err = capsys.readouterr().err
    assert "6557" in err
    assert "6558" in err


def test_set_livestatus_tcp_port_missing_xinetd_conf(tmp_path: Path) -> None:
    # Missing xinetd.conf. `omd config` just continues, which might be a mistake.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")

    result = _set_livestatus_tcp_port("mysite", "6557", omd_path=tmp_path)

    assert not isinstance(result, str)
