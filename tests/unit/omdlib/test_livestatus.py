#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.livestatus import (
    _write_livestatus_xinetd_conf_file,
    set_livestatus_tcp_instances,
    set_livestatus_tcp_per_source,
    set_livestatus_tcp_port,
)


def _make_site(sites_dir: Path, name: str, conf: str) -> None:
    etc = sites_dir / name / "etc/omd"
    etc.mkdir(parents=True, exist_ok=True)
    (etc / "site.conf").write_text(conf)


_DEFAULT_TCP_CONFIG: dict[str, str] = {
    "LIVESTATUS_TCP": "on",
    "LIVESTATUS_TCP_ONLY_FROM": "",
    "LIVESTATUS_TCP_PORT": "6557",
    "LIVESTATUS_TCP_INSTANCES": "500",
    "LIVESTATUS_TCP_PER_SOURCE": "250",
}


def test_write_livestatus_xinetd_conf_file_with_only_from(tmp_path: Path) -> None:
    # The only_from line is always present; the value must match what was passed.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    _write_livestatus_xinetd_conf_file(
        "mysite", "on", "192.168.0.0/24", "6557", "500", "250", tmp_path
    )
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    text = conf.read_text()
    assert "only_from       = 192.168.0.0/24" in text
    assert text.count("only_from") == 1


def test_write_livestatus_xinetd_conf_file_update_only_from(tmp_path: Path) -> None:
    # An already-set value is replaced.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    _write_livestatus_xinetd_conf_file(
        "mysite", "on", "10.0.0.2 10.0.0.3", "6557", "500", "250", tmp_path
    )
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    assert "only_from       = 10.0.0.2 10.0.0.3" in conf.read_text()
    assert "10.0.0.1" not in conf.read_text()


def test_write_livestatus_xinetd_conf_file_without_only_from(tmp_path: Path) -> None:
    # When only_from is empty, the line is still written with an empty value.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    _write_livestatus_xinetd_conf_file("mysite", "on", "", "6557", "500", "250", tmp_path)
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    assert "only_from       = " in conf.read_text()


def test_write_livestatus_xinetd_conf_file_off_writes_header_only(tmp_path: Path) -> None:
    # When LIVESTATUS_TCP is "off", a header-only file is written (no service block).
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    _write_livestatus_xinetd_conf_file("mysite", "off", "", "6557", "500", "250", tmp_path)

    assert conf.exists()
    assert "service livestatus" not in conf.read_text()


def test_write_livestatus_xinetd_conf_file_instances_in_output(tmp_path: Path) -> None:
    # The instances value is written into the config file.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    _write_livestatus_xinetd_conf_file("mysite", "on", "", "6557", "200", "250", tmp_path)
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    assert "instances       = 200" in conf.read_text()


def test_write_livestatus_xinetd_conf_file_per_source_in_output(tmp_path: Path) -> None:
    # The per_source value is written into the config file.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    _write_livestatus_xinetd_conf_file("mysite", "on", "", "6557", "500", "100", tmp_path)
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    assert "per_source      = 100" in conf.read_text()


def test_set_livestatus_tcp_port_writes_config(tmp_path: Path) -> None:
    # set_livestatus_tcp_port writes the given port to the config and returns it.
    # Conflict resolution is the caller's responsibility.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    result = set_livestatus_tcp_port("mysite", _DEFAULT_TCP_CONFIG, tmp_path, "6557")

    assert result == "6557"
    assert "port = 6557" in conf.read_text()


def test_set_livestatus_tcp_instances_updates_conf(tmp_path: Path) -> None:
    # New instances value is reflected in the config file; the value is returned.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    result = set_livestatus_tcp_instances("mysite", _DEFAULT_TCP_CONFIG, tmp_path, "300")

    assert result == "300"
    assert "instances       = 300" in conf.read_text()


def test_set_livestatus_tcp_instances_preserves_other_values(tmp_path: Path) -> None:
    # Changing instances does not alter cps or per_source in the written file.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")

    set_livestatus_tcp_instances("mysite", _DEFAULT_TCP_CONFIG, tmp_path, "300")
    text = (site_dir / "etc/xinetd.d/livestatusv1").read_text()

    assert "cps             = 100 3" in text
    assert "per_source      = 250" in text


def test_set_livestatus_tcp_per_source_updates_conf(tmp_path: Path) -> None:
    # New per_source value is reflected in the config file; the value is returned.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")
    conf = site_dir / "etc/xinetd.d/livestatusv1"

    result = set_livestatus_tcp_per_source("mysite", _DEFAULT_TCP_CONFIG, tmp_path, "50")

    assert result == "50"
    assert "per_source      = 50" in conf.read_text()


def test_set_livestatus_tcp_per_source_preserves_other_values(tmp_path: Path) -> None:
    # Changing per_source does not alter cps or instances in the written file.
    site_dir = tmp_path / "sites/mysite"
    _make_site(site_dir.parent, "mysite", "")

    set_livestatus_tcp_per_source("mysite", _DEFAULT_TCP_CONFIG, tmp_path, "50")
    text = (site_dir / "etc/xinetd.d/livestatusv1").read_text()

    assert "cps             = 100 3" in text
    assert "instances       = 500" in text
