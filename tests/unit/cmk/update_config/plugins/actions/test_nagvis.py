#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.update_config.internal import ExpiryVersion
from cmk.update_config.plugins.actions.nagvis import KeepNagVisForSitesWithMaps

LOGGER = logging.getLogger("test")


def _site(omd_root: Path, site_conf: str, *maps: str) -> None:
    (omd_root / "etc/omd").mkdir(parents=True)
    (omd_root / "etc/omd/site.conf").write_text(site_conf)
    (omd_root / "etc/nagvis/maps").mkdir(parents=True)
    for name in maps:
        (omd_root / "etc/nagvis/maps" / name).write_text("")


def _run_update(omd_root: Path, from_version: str) -> int:
    enabled = []
    KeepNagVisForSitesWithMaps(
        name="nagvis",
        title="NagVis",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_310,
        omd_root=omd_root,
        from_version=lambda: from_version,
        enable_nagvis=lambda: enabled.append(True),
    )(LOGGER)
    return len(enabled)


def test_keeps_nagvis_for_site_with_own_map(
    tmp_path: Path,
) -> None:
    _site(tmp_path, "CONFIG_NAGVIS='off'\n", "demo-germany.cfg", "datacenter.cfg")
    assert _run_update(tmp_path, "2.5.0p17.ultimate") == 1


def test_keeps_nagvis_on_update_from_stable_daily(
    tmp_path: Path,
) -> None:
    _site(tmp_path, "CONFIG_NAGVIS='off'\n", "datacenter.cfg")
    assert _run_update(tmp_path, "2.5.0-2026.10.20.ultimate") == 1


def test_warns_on_unparseable_from_version(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _site(tmp_path, "CONFIG_NAGVIS='off'\n", "datacenter.cfg")
    assert _run_update(tmp_path, "garbage.ultimate") == 0
    assert 'Cannot parse OMD_FROM_VERSION "garbage.ultimate"' in caplog.text


def test_leaves_nagvis_off_for_site_with_only_demo_maps(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _site(tmp_path, "CONFIG_NAGVIS='off'\n", "demo-germany.cfg")
    assert _run_update(tmp_path, "2.5.0p17.ultimate") == 0
    assert "NagVis is deprecated and has been switched off" in caplog.text


def test_leaves_nagvis_alone_on_later_updates(
    tmp_path: Path,
) -> None:
    _site(tmp_path, "CONFIG_NAGVIS='off'\n", "datacenter.cfg")
    assert _run_update(tmp_path, "3.0.0p1.pro") == 0


def test_leaves_site_without_nagvis_option_alone(
    tmp_path: Path,
) -> None:
    # Editions without NagVis, like Checkmk Cloud, have no NAGVIS option in site.conf
    _site(tmp_path, "CONFIG_CORE='cmc'\n", "datacenter.cfg")
    assert _run_update(tmp_path, "2.5.0p17.ultimate") == 0
