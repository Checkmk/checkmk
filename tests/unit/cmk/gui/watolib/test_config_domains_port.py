#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.gui.watolib.config_domains import _build_site_configs, _port_in_use_by


def _make_site(sites_dir: Path, name: str, conf: str) -> None:
    etc = sites_dir / name / "etc/omd"
    etc.mkdir(parents=True, exist_ok=True)
    (etc / "site.conf").write_text(conf)


def test_port_in_use_by_no_conflict(tmp_path: Path) -> None:
    # Port is not used by any site.
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "CONFIG_APACHE_TCP_PORT='5000'\n")

    site_configs = _build_site_configs(tmp_path)
    assert _port_in_use_by(6557, "mysite", site_configs) is None


def test_port_in_use_by_other_site(tmp_path: Path) -> None:
    # Another site uses the port on any key.
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "CONFIG_APACHE_TCP_PORT='5000'\n")
    _make_site(sites, "other", "CONFIG_APACHE_TCP_PORT='6557'\n")

    site_configs = _build_site_configs(tmp_path)
    assert _port_in_use_by(6557, "mysite", site_configs) == ("APACHE_TCP_PORT", "other")


def test_port_in_use_by_other_site_livestatus(tmp_path: Path) -> None:
    # Another site uses the port under LIVESTATUS_TCP_PORT.
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "CONFIG_APACHE_TCP_PORT='5000'\n")
    _make_site(sites, "other", "CONFIG_LIVESTATUS_TCP_PORT='6557'\n")

    site_configs = _build_site_configs(tmp_path)
    assert _port_in_use_by(6557, "mysite", site_configs) == ("LIVESTATUS_TCP_PORT", "other")


def test_port_in_use_by_current_site_non_livestatus(tmp_path: Path) -> None:
    # Current site uses the port under a key other than LIVESTATUS_TCP_PORT.
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "CONFIG_APACHE_TCP_PORT='6557'\n")

    site_configs = _build_site_configs(tmp_path)
    assert _port_in_use_by(6557, "mysite", site_configs) == ("APACHE_TCP_PORT", "mysite")


def test_port_in_use_by_current_site_livestatus_key_allowed(tmp_path: Path) -> None:
    # Current site has the port on LIVESTATUS_TCP_PORT itself.
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "CONFIG_LIVESTATUS_TCP_PORT='6557'\n")

    site_configs = _build_site_configs(tmp_path)
    assert _port_in_use_by(6557, "mysite", site_configs) is None


def test_port_in_use_by_missing_site_conf_skipped(tmp_path: Path) -> None:
    # A site directory with no site.conf is silently skipped.
    sites = tmp_path / "sites"
    (sites / "ghost").mkdir(parents=True)

    site_configs = _build_site_configs(tmp_path)
    assert _port_in_use_by(6557, "mysite", site_configs) is None


def test_port_in_use_by_commented_config_ignored(tmp_path: Path) -> None:
    # Commented-out CONFIG_ lines do not count as port usage.
    sites = tmp_path / "sites"
    _make_site(sites, "other", "# CONFIG_APACHE_TCP_PORT='6557'\n")

    site_configs = _build_site_configs(tmp_path)
    assert _port_in_use_by(6557, "mysite", site_configs) is None
