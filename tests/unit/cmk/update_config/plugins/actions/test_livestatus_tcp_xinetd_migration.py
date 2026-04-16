#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.update_config.plugins.actions.livestatus_tcp_xinetd_migration import (
    action,
)
from cmk.update_config.plugins.lib.livestatus_tcp_xinetd_migration import _DEFAULT_XINETD_CONF

LOGGER = logging.getLogger("test")

SITE_ID = "test"


def _build_site_root(tmp_path: Path) -> Path:
    """Site with LIVESTATUS_TCP on and a locally modified xinetd.conf."""
    site_root = Path(tmp_path)
    (site_root / "etc/omd").mkdir(parents=True)
    (site_root / "etc/omd/site.conf").write_text(
        "CONFIG_LIVESTATUS_TCP='on'\n"
        "CONFIG_LIVESTATUS_TCP_PORT='6558'\n"
        "CONFIG_LIVESTATUS_TCP_ONLY_FROM='0.0.0.0 ::/0'\n"
    )
    (site_root / "etc/xinetd.d").mkdir(parents=True)
    (site_root / "etc/mk-livestatus").mkdir(parents=True)
    livestatus_xinetd_config = site_root / "etc/mk-livestatus/xinetd.conf"
    livestatus_xinetd_config.write_text(
        _DEFAULT_XINETD_CONF.format(
            omd_site=SITE_ID,
            omd_root=str(site_root),
            livestatus_tcp_port=6558,
            livestatus_tcp_only_from="0.0.0.0 ::/0",
        )
    )
    (site_root / "etc/xinetd.d/mk-livestatus").symlink_to(livestatus_xinetd_config)
    return site_root


def test_action_no_local_modifications(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    site_root = _build_site_root(tmp_path)
    assert (site_root / "etc/xinetd.d/mk-livestatus").exists()
    assert (site_root / "etc/mk-livestatus/xinetd.conf").exists()
    with caplog.at_level(logging.INFO):
        action(LOGGER, site_root=site_root, site_id=SITE_ID)
    assert caplog.text == ""
    assert not (site_root / "etc/xinetd.d/mk-livestatus").exists()
    assert not (site_root / "etc/mk-livestatus/xinetd.conf").exists()


def test_action_backup_on_local_modifications(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    site_root = _build_site_root(tmp_path)
    (site_root / "etc/mk-livestatus/xinetd.conf").write_text("changes made")
    assert (site_root / "etc/xinetd.d/mk-livestatus").exists()
    assert (site_root / "etc/mk-livestatus/xinetd.conf").exists()
    with caplog.at_level(logging.INFO):
        action(LOGGER, site_root=site_root, site_id=SITE_ID)
    assert "Local modifications to xinetd config detected." in caplog.text
    assert (site_root / "etc/mk-livestatus/xinetd.conf.bak").exists()
    assert not (site_root / "etc/xinetd.d/mk-livestatus").exists()
    assert not (site_root / "etc/mk-livestatus/xinetd.conf").exists()


def test_no_livestatus_cleanup_old_xinetd_conf(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    site_root = _build_site_root(tmp_path)
    (site_root / "etc/xinetd.d/mk-livestatus").unlink()
    assert (site_root / "etc/mk-livestatus/xinetd.conf").exists()
    with caplog.at_level(logging.INFO):
        action(LOGGER, site_root=site_root, site_id=SITE_ID)
    assert "" in caplog.text
    assert not (site_root / "etc/mk-livestatus/xinetd.conf").exists()


def test_no_xinetd_conf_cleanup_symlink(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    site_root = _build_site_root(tmp_path)
    (site_root / "etc/mk-livestatus/xinetd.conf").unlink()
    assert (site_root / "etc/xinetd.d/mk-livestatus").is_symlink()
    with caplog.at_level(logging.INFO):
        action(LOGGER, site_root=site_root, site_id=SITE_ID)
    assert "" in caplog.text
    assert not (site_root / "etc/xinetd.d/mk-livestatus").is_symlink()


def test_action_idempotent(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    site_root = _build_site_root(tmp_path)
    assert (site_root / "etc/xinetd.d/mk-livestatus").exists()
    assert (site_root / "etc/mk-livestatus/xinetd.conf").exists()

    with caplog.at_level(logging.INFO):
        action(LOGGER, site_root=site_root, site_id=SITE_ID)
    assert "" in caplog.text
    assert not (site_root / "etc/xinetd.d/mk-livestatus").exists()
    assert not (site_root / "etc/mk-livestatus/xinetd.conf").exists()

    with caplog.at_level(logging.INFO):
        action(LOGGER, site_root=site_root, site_id=SITE_ID)
    assert "" in caplog.text
    assert not (site_root / "etc/xinetd.d/mk-livestatus").exists()
    assert not (site_root / "etc/mk-livestatus/xinetd.conf").exists()
