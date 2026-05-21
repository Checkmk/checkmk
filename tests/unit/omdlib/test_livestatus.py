#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.livestatus import write_livestatus_xinetd_conf

_DEFAULT_TCP_CONFIG: dict[str, str] = {
    "LIVESTATUS_TCP": "on",
    "LIVESTATUS_TCP_ONLY_FROM": "",
    "LIVESTATUS_TCP_PORT": "6557",
    "LIVESTATUS_TCP_INSTANCES": "500",
    "LIVESTATUS_TCP_PER_SOURCE": "250",
}


def _make_site(tmp_path: Path) -> Path:
    (tmp_path / "etc/omd").mkdir(parents=True)
    (tmp_path / "etc/omd/site.conf").write_text(
        "".join(f"CONFIG_{k}='{v}'\n" for k, v in _DEFAULT_TCP_CONFIG.items())
    )
    return tmp_path


def test_write_livestatus_xinetd_conf_with_only_from(tmp_path: Path) -> None:
    # The only_from line is always present; the value must match what was passed.
    site_home = _make_site(tmp_path)
    write_livestatus_xinetd_conf(
        "mysite", site_home, {**_DEFAULT_TCP_CONFIG, "LIVESTATUS_TCP_ONLY_FROM": "192.168.0.0/24"}
    )
    text = (site_home / "etc/xinetd.d/livestatusv1").read_text()
    assert "only_from       = 192.168.0.0/24" in text
    assert text.count("only_from") == 1


def test_write_livestatus_xinetd_conf_update_only_from(tmp_path: Path) -> None:
    # An already-set value is replaced.
    site_home = _make_site(tmp_path)
    write_livestatus_xinetd_conf(
        "mysite",
        site_home,
        {**_DEFAULT_TCP_CONFIG, "LIVESTATUS_TCP_ONLY_FROM": "10.0.0.2 10.0.0.3"},
    )
    assert (
        "only_from       = 10.0.0.2 10.0.0.3"
        in (site_home / "etc/xinetd.d/livestatusv1").read_text()
    )


def test_write_livestatus_xinetd_conf_without_only_from(tmp_path: Path) -> None:
    # When only_from is empty, the line is still written with an empty value.
    site_home = _make_site(tmp_path)
    write_livestatus_xinetd_conf("mysite", site_home, _DEFAULT_TCP_CONFIG)
    assert "only_from       = " in (site_home / "etc/xinetd.d/livestatusv1").read_text()


def test_write_livestatus_xinetd_conf_off_writes_header_only(tmp_path: Path) -> None:
    # When LIVESTATUS_TCP is "off", a header-only file is written (no service block).
    site_home = _make_site(tmp_path)
    conf = site_home / "etc/xinetd.d/livestatusv1"
    write_livestatus_xinetd_conf(
        "mysite", site_home, {**_DEFAULT_TCP_CONFIG, "LIVESTATUS_TCP": "off"}
    )
    assert conf.exists()
    assert "service livestatus" not in conf.read_text()


def test_write_livestatus_xinetd_conf_port_in_output(tmp_path: Path) -> None:
    site_home = _make_site(tmp_path)
    write_livestatus_xinetd_conf(
        "mysite", site_home, {**_DEFAULT_TCP_CONFIG, "LIVESTATUS_TCP_PORT": "6557"}
    )
    assert "port = 6557" in (site_home / "etc/xinetd.d/livestatusv1").read_text()


def test_write_livestatus_xinetd_conf_instances_in_output(tmp_path: Path) -> None:
    # The instances value is written into the config file.
    site_home = _make_site(tmp_path)
    write_livestatus_xinetd_conf(
        "mysite", site_home, {**_DEFAULT_TCP_CONFIG, "LIVESTATUS_TCP_INSTANCES": "200"}
    )
    assert "instances       = 200" in (site_home / "etc/xinetd.d/livestatusv1").read_text()


def test_write_livestatus_xinetd_conf_instances_preserves_other_values(tmp_path: Path) -> None:
    # Changing instances does not alter cps or per_source in the written file.
    site_home = _make_site(tmp_path)
    write_livestatus_xinetd_conf(
        "mysite", site_home, {**_DEFAULT_TCP_CONFIG, "LIVESTATUS_TCP_INSTANCES": "300"}
    )
    text = (site_home / "etc/xinetd.d/livestatusv1").read_text()
    assert "cps             = 100 3" in text
    assert "per_source      = 250" in text


def test_write_livestatus_xinetd_conf_per_source_in_output(tmp_path: Path) -> None:
    # The per_source value is written into the config file.
    site_home = _make_site(tmp_path)
    write_livestatus_xinetd_conf(
        "mysite", site_home, {**_DEFAULT_TCP_CONFIG, "LIVESTATUS_TCP_PER_SOURCE": "50"}
    )
    assert "per_source      = 50" in (site_home / "etc/xinetd.d/livestatusv1").read_text()


def test_write_livestatus_xinetd_conf_per_source_preserves_other_values(tmp_path: Path) -> None:
    # Changing per_source does not alter cps or instances in the written file.
    site_home = _make_site(tmp_path)
    write_livestatus_xinetd_conf(
        "mysite", site_home, {**_DEFAULT_TCP_CONFIG, "LIVESTATUS_TCP_PER_SOURCE": "50"}
    )
    text = (site_home / "etc/xinetd.d/livestatusv1").read_text()
    assert "cps             = 100 3" in text
    assert "instances       = 500" in text
