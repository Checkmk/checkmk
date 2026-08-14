#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.config_hooks import report_port_allocations


def _make_site(sites: Path, name: str, content: str | None) -> Path:
    site_conf = sites / name / "etc" / "omd" / "site.conf"
    site_conf.parent.mkdir(parents=True)
    if content is not None:
        site_conf.write_text(content)
    return site_conf


def test_report_port_allocations_all_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sites = tmp_path / "sites"
    _make_site(sites, "site1", "CONFIG_APACHE_TCP_PORT='5000'\n")
    _make_site(sites, "site2", "CONFIG_APACHE_TCP_PORT='5001'\n")

    report_port_allocations(tmp_path)

    assert capsys.readouterr().err == ""


def test_report_port_allocations_ignores_missing_site_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A site without site.conf (e.g. created with --no-init) allocates no ports.
    sites = tmp_path / "sites"
    _make_site(sites, "ghost", None)  # no site.conf
    (sites / "stray_file").write_text("ignored")  # non-directory entry — skipped silently

    report_port_allocations(tmp_path)

    assert capsys.readouterr().err == ""
