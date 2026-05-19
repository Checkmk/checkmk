#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.config_hooks import (
    _build_site_configs,
    _default_AGENT_RECEIVER_PORT,
    _default_APACHE_TCP_PORT,
    _default_LIVESTATUS_TCP_PORT,
    _default_RABBITMQ_DIST_PORT,
    _default_RABBITMQ_MANAGEMENT_PORT,
    _default_RABBITMQ_PORT,
    _default_TRACE_JAEGER_ADMIN_PORT,
    _next_free_port,
    _report_error,
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


def test_default_AGENT_RECEIVER_PORT_cross_key_conflict(tmp_path: Path) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "other", "CONFIG_LIVESTATUS_TCP_PORT='8000'\n")
    _make_site(sites, "mysite", "")

    site_configs = _build_site_configs("mysite", tmp_path)
    assert _default_AGENT_RECEIVER_PORT("mysite", site_configs) == "8001"


def test_default_AGENT_RECEIVER_PORT_warns_on_unreadable_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "")
    (sites / "ghost").mkdir(parents=True)

    site_configs = _build_site_configs("mysite", tmp_path)
    _default_AGENT_RECEIVER_PORT("mysite", site_configs)

    assert "ghost" in capsys.readouterr().err


def test_default_LIVESTATUS_TCP_PORT_cross_key_conflict(tmp_path: Path) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "other", "CONFIG_APACHE_TCP_PORT='6557'\n")
    _make_site(sites, "mysite", "")

    site_configs = _build_site_configs("mysite", tmp_path)
    assert _default_LIVESTATUS_TCP_PORT("mysite", site_configs) == "6558"


def test_default_LIVESTATUS_TCP_PORT_warns_on_unreadable_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "")
    (sites / "ghost").mkdir(parents=True)

    site_configs = _build_site_configs("mysite", tmp_path)
    _default_LIVESTATUS_TCP_PORT("mysite", site_configs)

    assert "ghost" in capsys.readouterr().err


def test_default_RABBITMQ_DIST_PORT_cross_key_conflict(tmp_path: Path) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "other", "CONFIG_RABBITMQ_PORT='25672'\n")
    _make_site(sites, "mysite", "")

    site_configs = _build_site_configs("mysite", tmp_path)
    assert _default_RABBITMQ_DIST_PORT("mysite", site_configs) == "25673"


def test_default_RABBITMQ_DIST_PORT_warns_on_unreadable_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "")
    (sites / "ghost").mkdir(parents=True)

    site_configs = _build_site_configs("mysite", tmp_path)
    _default_RABBITMQ_DIST_PORT("mysite", site_configs)

    assert "ghost" in capsys.readouterr().err


def test_default_RABBITMQ_MANAGEMENT_PORT_cross_key_conflict(tmp_path: Path) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "other", "CONFIG_RABBITMQ_PORT='15671'\n")
    _make_site(sites, "mysite", "")

    site_configs = _build_site_configs("mysite", tmp_path)
    assert _default_RABBITMQ_MANAGEMENT_PORT("mysite", site_configs) == "15672"


def test_default_RABBITMQ_MANAGEMENT_PORT_warns_on_unreadable_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "")
    (sites / "ghost").mkdir(parents=True)

    site_configs = _build_site_configs("mysite", tmp_path)
    _default_RABBITMQ_MANAGEMENT_PORT("mysite", site_configs)

    assert "ghost" in capsys.readouterr().err


def test_default_RABBITMQ_PORT_cross_key_conflict(tmp_path: Path) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "other", "CONFIG_RABBITMQ_DIST_PORT='5672'\n")
    _make_site(sites, "mysite", "")

    site_configs = _build_site_configs("mysite", tmp_path)
    assert _default_RABBITMQ_PORT("mysite", site_configs) == "5673"


def test_default_RABBITMQ_PORT_warns_on_unreadable_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "")
    (sites / "ghost").mkdir(parents=True)

    site_configs = _build_site_configs("mysite", tmp_path)
    _default_RABBITMQ_PORT("mysite", site_configs)

    assert "ghost" in capsys.readouterr().err


def test_default_TRACE_JAEGER_ADMIN_PORT_cross_key_conflict(tmp_path: Path) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "other", "CONFIG_TRACE_RECEIVE_PORT='14269'\n")
    _make_site(sites, "mysite", "")

    site_configs = _build_site_configs("mysite", tmp_path)
    assert _default_TRACE_JAEGER_ADMIN_PORT("mysite", site_configs) == "14270"


def test_default_TRACE_JAEGER_ADMIN_PORT_warns_on_unreadable_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "mysite", "")
    (sites / "ghost").mkdir(parents=True)

    site_configs = _build_site_configs("mysite", tmp_path)
    _default_TRACE_JAEGER_ADMIN_PORT("mysite", site_configs)

    assert "ghost" in capsys.readouterr().err


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
