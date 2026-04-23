#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.config_hooks import (
    _build_site_configs,
    _Error,
    _next_free_port,
    _report_error,
    _set_livestatus_tcp_only_from,
    _set_livestatus_tcp_port,
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


def _make_xinetd_conf(site_dir: Path, port: int) -> Path:
    conf = site_dir / "etc/mk-livestatus/xinetd.conf"
    conf.parent.mkdir(parents=True, exist_ok=True)
    conf.write_text(f"service livestatus\n{{\n\tport\t\t= {port}\n}}\n")
    return conf


def _make_xinetd_conf_with_only_from(site_dir: Path, only_from: str | None) -> Path:
    conf = site_dir / "etc/mk-livestatus/xinetd.conf"
    conf.parent.mkdir(parents=True, exist_ok=True)
    if only_from is None:
        # default: commented out, as in the shipped template
        only_from_line = "#\tonly_from       = 127.0.0.1\n"
    else:
        only_from_line = f"\tonly_from       = {only_from}\n"
    conf.write_text(f"service livestatus\n{{\n\tport\t\t= 6557\n{only_from_line}}}\n")
    return conf


def test_set_livestatus_tcp_port_no_conflict(tmp_path: Path) -> None:
    # Port is free. xinetd.conf is rewritten with the same port, value returned.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "CONFIG_LIVESTATUS_TCP_PORT='6557'\n")
    conf = _make_xinetd_conf(site_dir, 6557)

    site_configs = _build_site_configs("mysite", tmp_path)
    result = _set_livestatus_tcp_port("mysite", "6557", site_configs.configs, tmp_path)

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

    site_configs = _build_site_configs("mysite", tmp_path)
    result = _set_livestatus_tcp_port("mysite", "6557", site_configs.configs, tmp_path)

    assert result == "6558"
    assert "\tport\t\t= 6558" in conf.read_text()
    err = capsys.readouterr().err
    assert "6557" in err
    assert "6558" in err


def test_set_livestatus_tcp_port_missing_xinetd_conf(tmp_path: Path) -> None:
    # Missing xinetd.conf. `omd config` just continues, which might be a mistake.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")

    site_configs = _build_site_configs("mysite", tmp_path)
    result = _set_livestatus_tcp_port("mysite", "6557", site_configs.configs, tmp_path)

    assert isinstance(result, _Error)


def test_set_livestatus_tcp_only_from_commented_default(tmp_path: Path) -> None:
    # The shipped template has only_from commented out. Setting a value must uncomment
    # and replace it.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    conf = _make_xinetd_conf_with_only_from(site_dir, None)

    result = _set_livestatus_tcp_only_from("mysite", "192.168.0.0/24", tmp_path)

    assert result == "192.168.0.0/24"
    text = conf.read_text()
    assert "\tonly_from       = 192.168.0.0/24" in text
    assert text.count("only_from") == 1


def test_set_livestatus_tcp_only_from_existing_value(tmp_path: Path) -> None:
    # An already-set value is replaced.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    conf = _make_xinetd_conf_with_only_from(site_dir, "10.0.0.1")

    result = _set_livestatus_tcp_only_from("mysite", "10.0.0.2 10.0.0.3", tmp_path)

    assert result == "10.0.0.2 10.0.0.3"
    assert "\tonly_from       = 10.0.0.2 10.0.0.3" in conf.read_text()


@pytest.mark.xfail(reason="only_from absent from xinetd.conf is silently ignored", strict=True)
def test_set_livestatus_tcp_only_from_no_only_from_line(tmp_path: Path) -> None:
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    conf = _make_xinetd_conf(site_dir, 6557)  # no only_from line

    _set_livestatus_tcp_only_from("mysite", "10.0.0.1", tmp_path)

    assert "only_from" in conf.read_text()


def test_set_livestatus_tcp_only_from_missing_xinetd_conf(tmp_path: Path) -> None:
    # Missing xinetd.conf returns _Error without raising.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")

    result = _set_livestatus_tcp_only_from("mysite", "10.0.0.1", tmp_path)

    assert isinstance(result, _Error)
